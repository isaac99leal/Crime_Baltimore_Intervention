"""Convert finished bulk winery inventory into exact bottled physical inventory.

Packaging chemistry and physical inventory remain distinct concerns. This module
requires an explicit packaging assessment by default, but it does not reinterpret
that assessment as legal-release approval or infer closure performance from a
closure name.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .packaging import PackagingAssessment
from .winery_provenance import WineryLot, WineryProvenanceError, WineryProvenanceLedger


class BottlingLotConstraintError(ValueError):
    """Raised when a bulk lot cannot be converted into defensible bottle inventory."""


@dataclass(frozen=True)
class BottledLotManifest:
    lot: WineryLot
    source_lot_id: str
    bottle_count: int
    bottle_ml: int
    filled_volume_l: float
    input_volume_l: float
    bottling_loss_l: float
    packaging_oxygen_assessment_complete: bool
    tartrate_test_status: str
    packaging_warnings: tuple[str, ...]
    packaging_assessment: PackagingAssessment | None = None


def _is_bottled_stage(stage: str) -> bool:
    key = stage.strip().casefold().replace("-", "_").replace(" ", "_")
    return "bottl" in key or "packag" in key


def bottle_winery_lot(
    *,
    ledger: WineryProvenanceLedger,
    source_lot_id: str,
    bottled_lot_id: str,
    bottle_count: int,
    bottle_ml: int = 750,
    bottling_loss_l: float = 0.0,
    packaging_assessment: PackagingAssessment | None = None,
    require_packaging_assessment: bool = True,
) -> BottledLotManifest:
    """Consume finished bulk wine and create one exact bottled descendant lot.

    ``bottling_loss_l`` is explicit physical loss between the consumed source
    draw and filled bottles. It is never inferred from bottle size, producer,
    equipment, or wine style.
    """
    if not source_lot_id.strip():
        raise BottlingLotConstraintError("source_lot_id is required")
    if not bottled_lot_id.strip():
        raise BottlingLotConstraintError("bottled_lot_id is required")
    if isinstance(bottle_count, bool) or not isinstance(bottle_count, int) or bottle_count <= 0:
        raise BottlingLotConstraintError("bottle_count must be a positive integer")
    if isinstance(bottle_ml, bool) or not isinstance(bottle_ml, int) or not 50 <= bottle_ml <= 18_000:
        raise BottlingLotConstraintError("bottle_ml must be an integer within 50..18000")
    try:
        loss_l = float(bottling_loss_l)
    except (TypeError, ValueError) as exc:
        raise BottlingLotConstraintError("bottling_loss_l must be numeric") from exc
    if not math.isfinite(loss_l) or loss_l < 0.0:
        raise BottlingLotConstraintError("bottling_loss_l must be finite and non-negative")
    if require_packaging_assessment and packaging_assessment is None:
        raise BottlingLotConstraintError(
            "An explicit PackagingAssessment is required before physical bottling."
        )

    try:
        source = ledger.lots[source_lot_id]
    except KeyError as exc:
        raise BottlingLotConstraintError(f"Unknown winery source lot: {source_lot_id}") from exc
    if _is_bottled_stage(source.stage) or source.bottle_count is not None:
        raise BottlingLotConstraintError(
            f"Source lot {source_lot_id!r} is already in a bottled/packaged state."
        )

    filled_volume_l = (bottle_count * bottle_ml) / 1000.0
    input_volume_l = filled_volume_l + loss_l
    available = ledger.available_volume_l(source_lot_id)
    if input_volume_l > available + 1e-9:
        raise BottlingLotConstraintError(
            f"Bottling requires {input_volume_l:g} L but source has {available:g} L available."
        )

    try:
        bottled = ledger.transfer(
            source_lot_id,
            new_id=bottled_lot_id,
            stage="bottled",
            input_volume_l=input_volume_l,
            output_volume_l=filled_volume_l,
            bottle_count=bottle_count,
            bottle_ml=bottle_ml,
        )
    except WineryProvenanceError as exc:
        raise BottlingLotConstraintError(str(exc)) from exc

    if abs(bottled.volume_l - filled_volume_l) > max(0.001, filled_volume_l * 1e-8):
        raise BottlingLotConstraintError("Bottled lot volume does not match physical bottle fill volume.")
    if bottled.bottle_count != bottle_count or bottled.bottle_ml != bottle_ml:
        raise BottlingLotConstraintError("Bottled lot package metadata does not match bottling manifest.")

    assessment = packaging_assessment
    return BottledLotManifest(
        lot=bottled,
        source_lot_id=source_lot_id,
        bottle_count=bottle_count,
        bottle_ml=bottle_ml,
        filled_volume_l=filled_volume_l,
        input_volume_l=input_volume_l,
        bottling_loss_l=loss_l,
        packaging_oxygen_assessment_complete=(
            assessment.oxygen_assessment_complete if assessment is not None else False
        ),
        tartrate_test_status=(assessment.tartrate_test_status if assessment is not None else "unknown"),
        packaging_warnings=(assessment.warnings if assessment is not None else (
            "Packaging assessment was explicitly waived; bottle chemistry/stability state is unverified.",
        )),
        packaging_assessment=assessment,
    )
