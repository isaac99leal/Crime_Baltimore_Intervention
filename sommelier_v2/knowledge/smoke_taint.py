"""Cultivar-specific smoke-marker guide assessment.

This module compares measured grape markers with source-backed AWRI guide bands
for the cultivars represented in the recovered research corpus. It does not
infer smoke taint from smoke exposure alone, does not convert the guide bands
into a sensory diagnosis, and does not generalize one cultivar's thresholds to
another cultivar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .catalog import normalize_name
from .process_chemistry_evidence import ProcessChemistryEvidenceRegistry


class SmokeTaintConstraintError(ValueError):
    """Raised when a smoke-marker panel cannot be assessed defensibly."""


@dataclass(frozen=True)
class SmokeMarkerResult:
    marker: str
    measured_ug_kg: float
    moderate_guide_ug_kg: float
    high_guide_ug_kg: float
    guide_band: str


@dataclass(frozen=True)
class SmokeMarkerAssessment:
    cultivar: str
    status: str
    marker_results: tuple[SmokeMarkerResult, ...]
    ageing_expression_possible: bool
    warnings: tuple[str, ...]
    evidence_record_ids: tuple[str, ...]


_CULTIVAR_RECORDS = {
    normalize_name("Chardonnay"): "chem-smoke-risk-chardonnay",
    normalize_name("Pinot Noir"): "chem-smoke-risk-pinot-noir",
    normalize_name("Shiraz"): "chem-smoke-risk-shiraz",
}


def supported_smoke_guide_cultivars() -> tuple[str, ...]:
    return ("Chardonnay", "Pinot Noir", "Shiraz")


def assess_smoke_markers(
    *,
    cultivar: str,
    markers_ug_kg: Mapping[str, float],
    evidence: ProcessChemistryEvidenceRegistry | None = None,
) -> SmokeMarkerAssessment:
    """Compare measured grape smoke markers with cultivar-specific guide bands.

    Marker units are micrograms per kilogram of grapes because that is how the
    recovered guide tables are represented. Wine measurements or differently
    expressed analytical data must not be passed through this function.
    """
    if not cultivar.strip():
        raise SmokeTaintConstraintError("cultivar is required")
    record_id = _CULTIVAR_RECORDS.get(normalize_name(cultivar))
    if record_id is None:
        raise SmokeTaintConstraintError(
            f"No cultivar-specific smoke-marker guide is registered for {cultivar!r}; "
            "do not substitute thresholds from another cultivar."
        )
    if not markers_ug_kg:
        raise SmokeTaintConstraintError("At least one measured grape marker is required")

    registry = evidence or ProcessChemistryEvidenceRegistry()
    record = registry.record(record_id)
    if record is None:
        raise SmokeTaintConstraintError(f"Missing smoke evidence record {record_id}")
    guide = record.measurement("moderateHighRiskUgKg")
    if not isinstance(guide, Mapping):
        raise SmokeTaintConstraintError(
            f"Smoke evidence {record_id} lacks a marker guide mapping"
        )

    results: list[SmokeMarkerResult] = []
    rank = 0
    for marker, measured_raw in markers_ug_kg.items():
        if marker not in guide:
            raise SmokeTaintConstraintError(
                f"Marker {marker!r} is not present in the published {record.condition('cultivar')} guide panel"
            )
        if not isinstance(measured_raw, (int, float)) or isinstance(measured_raw, bool):
            raise SmokeTaintConstraintError(f"Marker {marker!r} must be numeric")
        measured = float(measured_raw)
        if measured < 0.0:
            raise SmokeTaintConstraintError(f"Marker {marker!r} cannot be negative")
        band = guide[marker]
        if not isinstance(band, tuple) or len(band) != 2:
            raise SmokeTaintConstraintError(
                f"Marker guide {record_id}.{marker} must contain moderate/high values"
            )
        moderate = float(band[0])
        high = float(band[1])
        if high < moderate:
            raise SmokeTaintConstraintError(
                f"Marker guide {record_id}.{marker} has high value below moderate value"
            )
        if measured < moderate:
            label = "below_published_moderate_guide"
            marker_rank = 0
        elif high > moderate and measured < high:
            label = "within_published_moderate_to_high_band"
            marker_rank = 1
        else:
            label = "at_or_above_published_high_guide"
            marker_rank = 2
        rank = max(rank, marker_rank)
        results.append(
            SmokeMarkerResult(
                marker=marker,
                measured_ug_kg=measured,
                moderate_guide_ug_kg=moderate,
                high_guide_ug_kg=high,
                guide_band=label,
            )
        )

    if rank == 0:
        status = "all_measured_markers_below_published_moderate_guides"
    elif rank == 1:
        status = "one_or_more_markers_in_published_moderate_to_high_band"
    else:
        status = "one_or_more_markers_at_or_above_published_high_guide"

    warnings = (
        "Smoke-marker guide bands are analytical risk guides, not universal sensory cutoffs or a smoke-taint diagnosis.",
        "Smoke-derived glycosides can release volatile phenols during fermentation, barrel or bottle ageing; expression can change with time.",
        "Mitigation or remediation can change wine composition and style and must not be modeled as cost-free removal of smoke risk.",
    )
    return SmokeMarkerAssessment(
        cultivar=str(record.condition("cultivar")),
        status=status,
        marker_results=tuple(results),
        ageing_expression_possible=True,
        warnings=warnings,
        evidence_record_ids=(
            "chem-smoke-taint-pathway",
            "chem-smoke-markers",
            record_id,
            "chem-smoke-remediation-style-cost",
        ),
    )
