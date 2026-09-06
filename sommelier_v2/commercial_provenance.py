"""Bridge physical winery provenance into commercial restaurant inventory.

This module performs a narrow custody transfer. It does not establish protected-
origin legality, release eligibility, sensory truth, or market value. Those remain
separate knowledge and legal layers.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

from .domain import (
    BeverageProgram,
    InventoryLot,
    InventoryPackagingSnapshot,
    InventoryProvenanceComponent,
    WineRecord,
)
from .inventory import InventoryManager
from .knowledge.bottling_lot import BottledLotManifest
from .knowledge.packaging import PackagingAssessment
from .knowledge.winery_provenance import (
    LotMovement,
    WineryLot,
    WineryProvenanceLedger,
)


class CommercialProvenanceError(ValueError):
    """Raised when a physical lot cannot enter commercial bottle inventory."""


@dataclass(frozen=True)
class CommercialDispatchResult:
    inventory_lot: InventoryLot
    movement: LotMovement
    dispatched_volume_l: float
    acquisition_cost: float
    provenance_fingerprint: str


def inventory_provenance_components(
    source: WineryLot,
) -> tuple[InventoryProvenanceComponent, ...]:
    """Normalize absolute winery provenance into deterministic percentages."""
    if source.volume_l <= 0.0:
        raise CommercialProvenanceError("Source winery lot has no physical volume.")

    grouped: dict[
        tuple[str, str, tuple[str, ...], int | None, tuple[str, ...], tuple[str, ...]],
        float,
    ] = {}
    for row in source.provenance:
        key = (
            row.grape,
            row.country,
            tuple(row.origins),
            row.vintage,
            tuple(row.block_ids),
            tuple(row.source_lot_ids),
        )
        grouped[key] = grouped.get(key, 0.0) + row.volume_l

    components = [
        InventoryProvenanceComponent(
            volume_pct=(liters / source.volume_l) * 100.0,
            grape=grape,
            country=country,
            origins=origins,
            vintage=vintage,
            block_ids=block_ids,
            source_lot_ids=source_lot_ids,
        )
        for (
            grape,
            country,
            origins,
            vintage,
            block_ids,
            source_lot_ids,
        ), liters in grouped.items()
    ]
    components.sort(
        key=lambda item: (
            item.country.casefold(),
            item.grape.casefold(),
            item.vintage if item.vintage is not None else -1,
            item.origins,
            item.block_ids,
            item.source_lot_ids,
        )
    )
    total = sum(item.volume_pct for item in components)
    if abs(total - 100.0) > 1e-6:
        raise CommercialProvenanceError(
            f"Normalized provenance must total 100%; got {total:.9f}%"
        )
    return tuple(components)


def packaging_snapshot_from_assessment(
    assessment: PackagingAssessment,
) -> InventoryPackagingSnapshot:
    """Translate immutable packaging evidence into a serializable business snapshot."""
    return InventoryPackagingSnapshot(
        oxygen_assessment_complete=assessment.oxygen_assessment_complete,
        ageing_oxygen_modifier=assessment.ageing_oxygen_modifier,
        prebottling_oxygen_risk_index=assessment.prebottling_oxygen_risk_index,
        closure_oxygen_exposure_prior=assessment.closure_oxygen_exposure_prior,
        molecular_so2_before_packaging_mg_l=assessment.molecular_so2_before_packaging_mg_l,
        tartrate_test_status=assessment.tartrate_test_status,
        tartrate_physical_instability_risk=assessment.tartrate_physical_instability_risk,
        warnings=tuple(assessment.warnings),
        evidence_record_ids=tuple(assessment.evidence_record_ids),
    )


def provenance_fingerprint(source: WineryLot) -> str:
    """Return a deterministic SHA-256 fingerprint for one physical lot lineage."""
    components = inventory_provenance_components(source)
    payload = {
        "source_winery_lot_id": source.id,
        "stage": source.stage,
        "bottle_count": source.bottle_count,
        "bottle_ml": source.bottle_ml,
        "components": [
            {
                "volume_pct": round(item.volume_pct, 9),
                "grape": item.grape,
                "country": item.country,
                "origins": list(item.origins),
                "vintage": item.vintage,
                "block_ids": list(item.block_ids),
                "source_lot_ids": list(item.source_lot_ids),
            }
            for item in components
        ],
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_bottled_stage(stage: str) -> bool:
    key = stage.strip().casefold().replace("-", "_").replace(" ", "_")
    return (
        "bottl" in key
        or "packag" in key
        or key in {"finished_wine", "commercial_release", "released_wine"}
    )


def _dispatch_packaged_lot(
    *,
    ledger: WineryProvenanceLedger,
    program: BeverageProgram,
    source_winery_lot_id: str,
    inventory_lot_id: str,
    wine: WineRecord,
    bottles: int,
    unit_cost: float,
    dispatch_reference: str,
    supplier_id: str,
    bottle_ml: int,
    glass_ml: int,
    open_bottle_life_days: int,
    require_bottled_stage: bool,
    packaging_snapshot: InventoryPackagingSnapshot | None,
) -> CommercialDispatchResult:
    if not source_winery_lot_id.strip():
        raise CommercialProvenanceError("source_winery_lot_id is required")
    if not inventory_lot_id.strip():
        raise CommercialProvenanceError("inventory_lot_id is required")
    if not dispatch_reference.strip():
        raise CommercialProvenanceError("dispatch_reference is required")
    if isinstance(bottles, bool) or not isinstance(bottles, int) or bottles <= 0:
        raise CommercialProvenanceError("bottles must be a positive integer")
    if isinstance(bottle_ml, bool) or not isinstance(bottle_ml, int) or bottle_ml <= 0:
        raise CommercialProvenanceError("bottle_ml must be a positive integer")
    if isinstance(glass_ml, bool) or not isinstance(glass_ml, int) or glass_ml <= 0:
        raise CommercialProvenanceError("glass_ml must be a positive integer")
    if glass_ml > bottle_ml:
        raise CommercialProvenanceError("glass_ml cannot exceed bottle_ml")
    if isinstance(open_bottle_life_days, bool) or not isinstance(open_bottle_life_days, int) or open_bottle_life_days <= 0:
        raise CommercialProvenanceError("open_bottle_life_days must be a positive integer")
    try:
        unit_cost_f = float(unit_cost)
    except (TypeError, ValueError) as exc:
        raise CommercialProvenanceError("unit_cost must be numeric") from exc
    if not math.isfinite(unit_cost_f) or unit_cost_f < 0.0:
        raise CommercialProvenanceError("unit_cost must be finite and non-negative")

    try:
        source = ledger.lots[source_winery_lot_id]
    except KeyError as exc:
        raise CommercialProvenanceError(
            f"Unknown winery source lot: {source_winery_lot_id}"
        ) from exc

    if require_bottled_stage and not _is_bottled_stage(source.stage):
        raise CommercialProvenanceError(
            f"Source lot stage {source.stage!r} is not a bottled/packaged commercial stage."
        )
    if source.bottle_count is None or source.bottle_ml is None:
        raise CommercialProvenanceError(
            "Source lot lacks physical bottle-count/fill-size metadata; a stage label alone cannot create sealed inventory."
        )
    if source.bottle_ml != bottle_ml:
        raise CommercialProvenanceError(
            f"Requested {bottle_ml} mL bottles do not match source package size {source.bottle_ml} mL."
        )

    available = ledger.available_volume_l(source_winery_lot_id)
    unit_l = source.bottle_ml / 1000.0
    available_bottles_f = available / unit_l
    available_bottles = round(available_bottles_f)
    if abs(available_bottles_f - available_bottles) > 1e-8:
        raise CommercialProvenanceError(
            "Available packaged volume is not aligned to whole source bottles."
        )
    if bottles > available_bottles:
        raise CommercialProvenanceError(
            f"Shipment requests {bottles} bottles but only {available_bottles} remain available."
        )
    dispatched_volume_l = bottles * unit_l

    components = inventory_provenance_components(source)
    fingerprint = provenance_fingerprint(source)
    inventory_lot = InventoryLot(
        lot_id=inventory_lot_id,
        wine=wine,
        sealed_bottles=bottles,
        unit_cost=unit_cost_f,
        received_day=program.day,
        supplier_id=supplier_id,
        bottle_ml=bottle_ml,
        glass_ml=glass_ml,
        open_bottle_life_days=open_bottle_life_days,
        source_winery_lot_id=source.id,
        source_dispatch_reference=dispatch_reference,
        provenance_fingerprint=fingerprint,
        provenance_components=components,
        packaging_snapshot=packaging_snapshot,
    )

    manager = InventoryManager(program)
    acquisition_cost = manager.validate_receive(inventory_lot)

    # No mutation above this line touches winery balances or program cash/inventory.
    movement = ledger.dispatch(
        source_winery_lot_id,
        volume_l=dispatched_volume_l,
        external_reference=dispatch_reference,
        reason="commercial_inventory_receipt",
    )
    program.cash -= acquisition_cost
    program.inventory[inventory_lot_id] = inventory_lot

    return CommercialDispatchResult(
        inventory_lot=inventory_lot,
        movement=movement,
        dispatched_volume_l=dispatched_volume_l,
        acquisition_cost=acquisition_cost,
        provenance_fingerprint=fingerprint,
    )


def dispatch_winery_lot_to_inventory(
    *,
    ledger: WineryProvenanceLedger,
    program: BeverageProgram,
    source_winery_lot_id: str,
    inventory_lot_id: str,
    wine: WineRecord,
    bottles: int,
    unit_cost: float,
    dispatch_reference: str,
    supplier_id: str = "",
    bottle_ml: int = 750,
    glass_ml: int = 150,
    open_bottle_life_days: int = 3,
    require_bottled_stage: bool = True,
) -> CommercialDispatchResult:
    """Move a packaged lot into inventory when packaging chemistry is unavailable.

    This is the compatibility path for imported or legacy packaged stock. It
    preserves physical provenance and bottle format but leaves
    ``InventoryLot.packaging_snapshot`` unknown. It never fabricates a chemistry
    record from the stage name, producer, closure, or bottle format.
    """
    return _dispatch_packaged_lot(
        ledger=ledger,
        program=program,
        source_winery_lot_id=source_winery_lot_id,
        inventory_lot_id=inventory_lot_id,
        wine=wine,
        bottles=bottles,
        unit_cost=unit_cost,
        dispatch_reference=dispatch_reference,
        supplier_id=supplier_id,
        bottle_ml=bottle_ml,
        glass_ml=glass_ml,
        open_bottle_life_days=open_bottle_life_days,
        require_bottled_stage=require_bottled_stage,
        packaging_snapshot=None,
    )


def dispatch_bottled_manifest_to_inventory(
    *,
    ledger: WineryProvenanceLedger,
    program: BeverageProgram,
    manifest: BottledLotManifest,
    inventory_lot_id: str,
    wine: WineRecord,
    bottles: int,
    unit_cost: float,
    dispatch_reference: str,
    supplier_id: str = "",
    glass_ml: int = 150,
    open_bottle_life_days: int = 3,
) -> CommercialDispatchResult:
    """Dispatch simulator-bottled wine while preserving its packaging assessment.

    The manifest must still identify the exact immutable packaged lot held by the
    ledger. A stale or cross-attached manifest fails before either winery or
    restaurant inventory mutates.
    """
    source_id = manifest.lot.id
    try:
        source = ledger.lots[source_id]
    except KeyError as exc:
        raise CommercialProvenanceError(
            f"Bottling manifest source lot {source_id!r} is not present in the winery ledger."
        ) from exc
    if source != manifest.lot:
        raise CommercialProvenanceError(
            "Bottling manifest does not match the immutable packaged lot stored in the ledger."
        )
    if manifest.bottle_count != source.bottle_count or manifest.bottle_ml != source.bottle_ml:
        raise CommercialProvenanceError(
            "Bottling manifest package count/format does not match the physical winery lot."
        )
    tolerance = max(0.001, source.volume_l * 1e-8)
    if abs(manifest.filled_volume_l - source.volume_l) > tolerance:
        raise CommercialProvenanceError(
            "Bottling manifest filled volume does not match the physical packaged lot."
        )

    snapshot = (
        packaging_snapshot_from_assessment(manifest.packaging_assessment)
        if manifest.packaging_assessment is not None
        else None
    )
    return _dispatch_packaged_lot(
        ledger=ledger,
        program=program,
        source_winery_lot_id=source_id,
        inventory_lot_id=inventory_lot_id,
        wine=wine,
        bottles=bottles,
        unit_cost=unit_cost,
        dispatch_reference=dispatch_reference,
        supplier_id=supplier_id,
        bottle_ml=manifest.bottle_ml,
        glass_ml=glass_ml,
        open_bottle_life_days=open_bottle_life_days,
        require_bottled_stage=True,
        packaging_snapshot=snapshot,
    )
