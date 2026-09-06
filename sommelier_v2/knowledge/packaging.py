"""Pre-bottling oxygen and physical-stability mechanics.

This module intentionally stays separate from finished-wine label validation.
Packaging chemistry does not change whether an origin or variety claim is legal.
It changes bottle condition and ageing risk.

Published dissolved-oxygen and SO2 values are used only as explicit guide
anchors. The risk transforms and ageing modifier are simulation priors. Closure
oxygen behavior is never inferred from a closure name; callers must provide an
explicit exposure prior when they want closure oxygen to affect the model.
"""
from __future__ import annotations

from dataclasses import dataclass

from .fermentation_chemistry import clamp, molecular_so2_mg_l
from .process_chemistry_evidence import ProcessChemistryEvidenceRegistry


class PackagingConstraintError(ValueError):
    """Raised when packaging inputs are outside the supported process envelope."""


TARTRATE_TEST_STATUSES = frozenset({"unknown", "tested_stable", "tested_unstable"})


@dataclass(frozen=True)
class PackagingPlan:
    prebottling_dissolved_oxygen_mg_l: float | None = None
    closure_oxygen_exposure_prior: float | None = None
    tartrate_test_status: str = "unknown"
    cold_stabilization_performed: bool = False


@dataclass(frozen=True)
class PackagingAssessment:
    prebottling_oxygen_risk_index: float | None
    closure_oxygen_exposure_prior: float | None
    oxygen_assessment_complete: bool
    ageing_oxygen_modifier: float
    free_so2_cost_guide_upper_mg_l: float | None
    molecular_so2_before_packaging_mg_l: float
    tartrate_test_status: str
    tartrate_physical_instability_risk: float | None
    warnings: tuple[str, ...]
    evidence_record_ids: tuple[str, ...]


def _numeric_measurement(
    registry: ProcessChemistryEvidenceRegistry,
    record_id: str,
    name: str,
) -> float:
    record = registry.record(record_id)
    if record is None:
        raise PackagingConstraintError(f"Missing chemistry evidence record {record_id}")
    value = record.measurement(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise PackagingConstraintError(
            f"Evidence {record_id}.{name} is not a numeric guide value"
        )
    return float(value)


def assess_packaging(
    *,
    ph: float,
    free_so2_mg_l: float,
    plan: PackagingPlan = PackagingPlan(),
    evidence: ProcessChemistryEvidenceRegistry | None = None,
) -> PackagingAssessment:
    """Assess packaging oxygen exposure and tartrate-test state.

    The returned ``free_so2_cost_guide_upper_mg_l`` is a published guide upper
    bound based on measured dissolved oxygen. It is not subtracted from the wine
    as if it were exact bottle stoichiometry.
    """
    if not 2.0 <= ph <= 5.0:
        raise PackagingConstraintError("pH must be within 2.0..5.0")
    if not 0.0 <= free_so2_mg_l <= 300.0:
        raise PackagingConstraintError("free_so2_mg_l must be within 0..300")
    if plan.prebottling_dissolved_oxygen_mg_l is not None and not (
        0.0 <= plan.prebottling_dissolved_oxygen_mg_l <= 20.0
    ):
        raise PackagingConstraintError(
            "prebottling_dissolved_oxygen_mg_l must be within 0..20"
        )
    if plan.closure_oxygen_exposure_prior is not None and not (
        0.0 <= plan.closure_oxygen_exposure_prior <= 1.0
    ):
        raise PackagingConstraintError(
            "closure_oxygen_exposure_prior must be within 0..1"
        )
    tartrate_status = plan.tartrate_test_status.strip().casefold()
    if tartrate_status not in TARTRATE_TEST_STATUSES:
        raise PackagingConstraintError(
            f"Unsupported tartrate_test_status {plan.tartrate_test_status!r}"
        )

    registry = evidence or ProcessChemistryEvidenceRegistry()
    warnings: list[str] = []
    evidence_ids = [
        "chem-prebottling-dissolved-oxygen",
        "chem-oxygen-so2-demand",
        "chem-closure-oxygen-transmission",
        "chem-tartrate-stability",
        "chem-cold-stability-not-sensory-fault",
    ]

    do_risk: float | None = None
    so2_cost_upper: float | None = None
    if plan.prebottling_dissolved_oxygen_mg_l is None:
        warnings.append(
            "Pre-bottling dissolved oxygen is unknown; no dissolved-oxygen risk value is inferred."
        )
    else:
        target = _numeric_measurement(
            registry,
            "chem-prebottling-dissolved-oxygen",
            "generalTargetBeforeBottlingMgLLessThan",
        )
        high_anchor = _numeric_measurement(
            registry,
            "chem-prebottling-dissolved-oxygen",
            "possibleDissolvedOxygenAfterMovementMgL",
        )
        if high_anchor <= target:
            raise PackagingConstraintError("Invalid dissolved-oxygen evidence anchors")
        do_value = plan.prebottling_dissolved_oxygen_mg_l
        do_risk = clamp((do_value - target) / (high_anchor - target))
        guide_cost = _numeric_measurement(
            registry,
            "chem-oxygen-so2-demand",
            "guideFreeSo2CostMgLPer1MgLOxygenUpTo",
        )
        so2_cost_upper = do_value * guide_cost
        if do_value >= high_anchor:
            warnings.append(
                "Measured dissolved oxygen is at or above the high packaging-exposure guide anchor."
            )
        elif do_value >= target:
            warnings.append(
                "Measured dissolved oxygen is above the general pre-bottling guide target."
            )

    closure_prior = plan.closure_oxygen_exposure_prior
    if closure_prior is None:
        warnings.append(
            "Closure oxygen exposure is unknown; the simulator does not infer transmission from closure type or name."
        )

    # Higher modifiers accelerate the existing continuous bottle-age model.
    # The weights below are derived simulator priors, not published OTR equations.
    ageing_oxygen_modifier = 1.0
    if do_risk is not None:
        ageing_oxygen_modifier += 0.85 * do_risk
    if closure_prior is not None:
        ageing_oxygen_modifier += 0.55 * closure_prior

    if tartrate_status == "tested_stable":
        tartrate_risk: float | None = 0.0
    elif tartrate_status == "tested_unstable":
        tartrate_risk = 1.0
        warnings.append(
            "The wine is test-confirmed tartrate-unstable; this is modeled as a physical stability issue, not microbial spoilage."
        )
    else:
        tartrate_risk = None
        if plan.cold_stabilization_performed:
            warnings.append(
                "Cold stabilization was performed, but no stability-test result is supplied; process history does not prove current tartrate stability."
            )
        else:
            warnings.append(
                "Tartrate stability is unknown; no instability score is inferred from pH or process history."
            )

    return PackagingAssessment(
        prebottling_oxygen_risk_index=do_risk,
        closure_oxygen_exposure_prior=closure_prior,
        oxygen_assessment_complete=(
            plan.prebottling_dissolved_oxygen_mg_l is not None
            and closure_prior is not None
        ),
        ageing_oxygen_modifier=ageing_oxygen_modifier,
        free_so2_cost_guide_upper_mg_l=so2_cost_upper,
        molecular_so2_before_packaging_mg_l=molecular_so2_mg_l(free_so2_mg_l, ph),
        tartrate_test_status=tartrate_status,
        tartrate_physical_instability_risk=tartrate_risk,
        warnings=tuple(warnings),
        evidence_record_ids=tuple(evidence_ids),
    )
