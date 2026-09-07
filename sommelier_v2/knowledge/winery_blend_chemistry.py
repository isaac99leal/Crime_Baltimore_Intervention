"""Atomic bridge between winery provenance draws and blend chemistry.

The physical provenance ledger remains authoritative for custody and liters.
Chemistry may describe those same draws, but it cannot independently choose a
source set or volume. The bridge validates that the chemistry ledger matches the
physical operation exactly, computes chemistry before any physical mutation, and
only then asks :class:`WineryProvenanceLedger` to consume the wine.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Sequence

from .blend_chemistry import (
    BlendChemistryComponent,
    BlendChemistryResult,
    BlendPostMixMeasurements,
    blend_chemistry,
)
from .winery_provenance import LotMovement, WineryLot, WineryProvenanceLedger


class WineryBlendChemistryConstraintError(ValueError):
    """Raised when physical blend draws and chemistry inputs disagree."""


@dataclass(frozen=True)
class WineryBlendChemistryResult:
    lot: WineryLot
    chemistry: BlendChemistryResult
    movement: LotMovement


def _physical_draw(value: float, *, source_id: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise WineryBlendChemistryConstraintError(
            f"Physical draw for {source_id} must be a real numeric value; got {value!r}"
        )
    draw = float(value)
    if not isfinite(draw) or draw <= 0:
        raise WineryBlendChemistryConstraintError(
            f"Physical draw for {source_id} must be finite and positive; got {value!r}"
        )
    return draw


def blend_winery_lots_with_chemistry(
    ledger: WineryProvenanceLedger,
    source_lot_ids: Sequence[str],
    chemistry_components: Sequence[BlendChemistryComponent],
    *,
    new_id: str,
    draws_l: Sequence[float] | None = None,
    stage: str = "blend",
    post_mix: BlendPostMixMeasurements | None = None,
    operation_oxygen_delta_mg: float | None = None,
) -> WineryBlendChemistryResult:
    """Create one physical blend and chemistry result from exactly the same draws.

    ``source_lot_ids`` and the physical draw volumes are authoritative. Chemistry
    components may arrive in any order, but they must contain exactly one entry
    for every physical source and each ``draw_l`` must match the physical draw.

    Chemistry is calculated first. Therefore chemistry validation failure cannot
    consume winery inventory. The provenance ledger then performs its own full
    atomic validation before consuming any source balance.
    """

    source_ids = tuple(source_lot_ids)
    if not source_ids:
        raise WineryBlendChemistryConstraintError("At least one physical source lot is required.")
    if any(not isinstance(source_id, str) or not source_id.strip() for source_id in source_ids):
        raise WineryBlendChemistryConstraintError("Every physical source lot ID must be non-empty text.")
    if len(set(source_ids)) != len(source_ids):
        raise WineryBlendChemistryConstraintError(
            "A physical source lot may appear only once in one blend operation."
        )

    if draws_l is None:
        draws = tuple(
            _physical_draw(ledger.available_volume_l(source_id), source_id=source_id)
            for source_id in source_ids
        )
    else:
        if len(draws_l) != len(source_ids):
            raise WineryBlendChemistryConstraintError(
                "draws_l must have one physical volume for each source lot."
            )
        draws = tuple(
            _physical_draw(value, source_id=source_id)
            for source_id, value in zip(source_ids, draws_l)
        )

    chemistry_rows = tuple(chemistry_components)
    if len(chemistry_rows) != len(source_ids):
        raise WineryBlendChemistryConstraintError(
            "Chemistry must contain exactly one component for every physical source lot."
        )
    by_source: dict[str, BlendChemistryComponent] = {}
    for row in chemistry_rows:
        if row.source_id in by_source:
            raise WineryBlendChemistryConstraintError(
                f"Duplicate chemistry source lot ID: {row.source_id}"
            )
        by_source[row.source_id] = row
    if set(by_source) != set(source_ids):
        missing = tuple(source_id for source_id in source_ids if source_id not in by_source)
        extra = tuple(source_id for source_id in by_source if source_id not in set(source_ids))
        raise WineryBlendChemistryConstraintError(
            f"Chemistry source IDs must exactly match physical source IDs; missing={missing}, extra={extra}."
        )

    ordered_rows: list[BlendChemistryComponent] = []
    for source_id, draw in zip(source_ids, draws):
        row = by_source[source_id]
        tolerance = max(1e-9, draw * 1e-10)
        if abs(float(row.draw_l) - draw) > tolerance:
            raise WineryBlendChemistryConstraintError(
                f"Chemistry draw for {source_id} ({row.draw_l:g} L) does not match physical draw ({draw:g} L)."
            )
        ordered_rows.append(row)

    chemistry = blend_chemistry(
        tuple(ordered_rows),
        post_mix=post_mix,
        operation_oxygen_delta_mg=operation_oxygen_delta_mg,
    )

    # WineryProvenanceLedger.blend validates IDs, availability, package state and
    # every draw before mutation, then consumes all sources atomically.
    lot = ledger.blend(
        source_ids,
        new_id=new_id,
        draws_l=draws,
        stage=stage,
    )
    movement = ledger.movements[-1]
    return WineryBlendChemistryResult(lot=lot, chemistry=chemistry, movement=movement)
