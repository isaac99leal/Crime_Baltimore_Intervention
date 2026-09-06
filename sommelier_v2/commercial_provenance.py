"""Bridge physical winery provenance into commercial restaurant inventory.

This module performs a narrow custody transfer. It does not establish protected-
origin legality, release eligibility, sensory truth, or market value. Those remain
separate knowledge and legal layers.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .domain import (
    BeverageProgram,
    InventoryLot,
    InventoryProvenanceComponent,
    WineRecord,
)
from .inventory import InventoryManager
from .knowledge.winery_provenance import (
    LotMovement,
    WineryLot,
    WineryProvenanceError,
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


def provenance_fingerprint(source: WineryLot) -> str:
    """Return a deterministic SHA-256 fingerprint for one physical lot lineage."""
    components = inventory_provenance_components(source)
    payload = {
        "source_winery_lot_id": source.id,
        "stage": source.stage,
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
    """Atomically move bottled wine from winery custody into restaurant inventory.

    The physical source is checked before the commercial receipt. Restaurant
    receipt is then preflighted without mutating program cash/inventory. Only
    after every validation succeeds is the winery source consumed and the
    restaurant receipt committed.
    """
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
    if unit_cost < 0.0:
        raise CommercialProvenanceError("unit_cost cannot be negative")

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

    dispatched_volume_l = (bottles * bottle_ml) / 1000.0
    available = ledger.available_volume_l(source_winery_lot_id)
    if dispatched_volume_l > available + 1e-9:
        raise CommercialProvenanceError(
            f"Shipment requires {dispatched_volume_l:g} L but source has {available:g} L available."
        )

    components = inventory_provenance_components(source)
    fingerprint = provenance_fingerprint(source)
    inventory_lot = InventoryLot(
        lot_id=inventory_lot_id,
        wine=wine,
        sealed_bottles=bottles,
        unit_cost=float(unit_cost),
        received_day=program.day,
        supplier_id=supplier_id,
        bottle_ml=bottle_ml,
        glass_ml=glass_ml,
        open_bottle_life_days=open_bottle_life_days,
        source_winery_lot_id=source.id,
        source_dispatch_reference=dispatch_reference,
        provenance_fingerprint=fingerprint,
        provenance_components=components,
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
