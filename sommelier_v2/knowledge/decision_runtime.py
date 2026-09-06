"""Apply validated winemaking decisions to executable process state.

The decision matrix contains more choices than the current kinetic/runtime model
can represent. This bridge applies only mappings that have a clear mechanical
meaning. Qualitative choices that would require an analytical value stay
unresolved unless the caller supplies that value explicitly.

Protected-designation execution is fail closed. A selected decision marked as
requiring a designation check must have an explicit option-level legal
confirmation or a confirmation supplied by the reviewed legal-practice bridge.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Mapping

from .fermentation_process import FermentationPlan, MustComposition
from .legal_practice_bridge import LegalPracticeBridge
from .legal_specs import LegalWineSpec
from .packaging import PackagingPlan
from .winemaking_decisions import WinemakingDecisionRegistry


class DecisionRuntimeError(ValueError):
    """Raised when a selected decision cannot be executed safely."""


@dataclass(frozen=True)
class DecisionRuntimeInputs:
    """Explicit measurements/priors required by qualitative decision labels."""

    partial_whole_cluster_fraction: float | None = None
    juice_turbidity_ntu: float | None = None
    prebottling_dissolved_oxygen_mg_l: float | None = None
    closure_oxygen_exposure_prior: float | None = None


@dataclass(frozen=True)
class DecisionRuntimeApplication:
    decision_id: str
    option_id: str
    status: str
    note: str


@dataclass(frozen=True)
class DecisionRuntimeResult:
    must: MustComposition
    fermentation_plan: FermentationPlan
    packaging_plan: PackagingPlan
    axis_effects: Mapping[str, float]
    applications: tuple[DecisionRuntimeApplication, ...]

    @property
    def unresolved(self) -> tuple[DecisionRuntimeApplication, ...]:
        return tuple(
            item
            for item in self.applications
            if item.status in {"requires_measurement", "runtime_not_implemented"}
        )


# These are explicit simulator priors, not published oxygen-dose equations.
OXYGEN_MANAGEMENT_PRIORS = MappingProxyType(
    {
        "protected": 0.15,
        "moderate": 0.50,
        "oxygenated": 0.80,
    }
)


def _confirmation_key(decision_id: str, option_id: str) -> str:
    return f"{decision_id}:{option_id}"


def _validate_runtime_inputs(inputs: DecisionRuntimeInputs) -> None:
    if inputs.partial_whole_cluster_fraction is not None and not (
        0.0 < inputs.partial_whole_cluster_fraction < 1.0
    ):
        raise DecisionRuntimeError("partial_whole_cluster_fraction must be strictly between 0 and 1")
    if inputs.juice_turbidity_ntu is not None and not (0.0 <= inputs.juice_turbidity_ntu <= 5000.0):
        raise DecisionRuntimeError("juice_turbidity_ntu must be within 0..5000")
    if inputs.prebottling_dissolved_oxygen_mg_l is not None and not (
        0.0 <= inputs.prebottling_dissolved_oxygen_mg_l <= 20.0
    ):
        raise DecisionRuntimeError("prebottling_dissolved_oxygen_mg_l must be within 0..20")
    if inputs.closure_oxygen_exposure_prior is not None and not (
        0.0 <= inputs.closure_oxygen_exposure_prior <= 1.0
    ):
        raise DecisionRuntimeError("closure_oxygen_exposure_prior must be within 0..1")


def _legal_confirmation(
    *,
    decision_id: str,
    option_id: str,
    legal_spec: LegalWineSpec | None,
    explicit_confirmations: Mapping[str, bool],
    legal_bridge: LegalPracticeBridge,
) -> bool | None:
    key = _confirmation_key(decision_id, option_id)
    if key in explicit_confirmations:
        value = explicit_confirmations[key]
        if not isinstance(value, bool):
            raise DecisionRuntimeError(f"Legal confirmation {key!r} must be boolean")
        return value
    if legal_spec is None:
        return None
    return legal_bridge.assess_option(legal_spec, decision_id, option_id).legal_confirmation


def _apply_axis_effects(
    axis_totals: dict[str, float],
    option_matrix: Mapping[str, float],
) -> None:
    for axis, value in option_matrix.items():
        axis_totals[axis] = max(-1.0, min(1.0, axis_totals.get(axis, 0.0) + float(value)))


def apply_winemaking_decisions(
    selections: Mapping[str, str],
    *,
    must: MustComposition,
    fermentation_plan: FermentationPlan,
    packaging_plan: PackagingPlan = PackagingPlan(),
    runtime_inputs: DecisionRuntimeInputs = DecisionRuntimeInputs(),
    protected_designation: bool = False,
    legal_spec: LegalWineSpec | None = None,
    legal_confirmations: Mapping[str, bool] | None = None,
    decisions: WinemakingDecisionRegistry | None = None,
    legal_bridge: LegalPracticeBridge | None = None,
) -> DecisionRuntimeResult:
    """Apply selected decision options to the current executable model.

    ``legal_confirmations`` is option-specific and uses keys of the form
    ``"decision-id:option-id"``. It represents a reviewed external legal result,
    not a simulator guess.
    """
    _validate_runtime_inputs(runtime_inputs)
    registry = decisions or WinemakingDecisionRegistry()
    bridge = legal_bridge or LegalPracticeBridge(registry)
    confirmations = legal_confirmations or {}

    current_must = must
    current_plan = fermentation_plan
    current_packaging = packaging_plan
    axis_effects = {axis: 0.0 for axis in registry.axes}
    applications: list[DecisionRuntimeApplication] = []

    for decision_id, option_id in selections.items():
        decision = registry.decision(decision_id)
        if decision is None:
            raise DecisionRuntimeError(f"Unknown winemaking decision {decision_id!r}")
        option = decision.option(option_id)
        if option is None:
            raise DecisionRuntimeError(
                f"Unknown option {option_id!r} for decision {decision_id!r}"
            )

        if protected_designation and decision.requires_designation_check:
            confirmation = _legal_confirmation(
                decision_id=decision.id,
                option_id=option.id,
                legal_spec=legal_spec,
                explicit_confirmations=confirmations,
                legal_bridge=bridge,
            )
            if confirmation is False:
                raise DecisionRuntimeError(
                    f"{decision.id}/{option.id} is prohibited by the supplied legal authority"
                )
            if confirmation is not True:
                raise DecisionRuntimeError(
                    f"{decision.id}/{option.id} requires explicit legal confirmation for a protected designation"
                )

        _apply_axis_effects(axis_effects, option.matrix)

        if decision.id == "destemming":
            p = current_plan.alcoholic_params
            if option.id == "full":
                current_plan = replace(
                    current_plan,
                    alcoholic_params=replace(p, whole_cluster_fraction=0.0),
                )
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", "Set whole-cluster fraction to 0."))
            elif option.id == "whole-cluster":
                current_plan = replace(
                    current_plan,
                    alcoholic_params=replace(p, whole_cluster_fraction=1.0),
                )
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", "Set whole-cluster fraction to 1."))
            else:
                fraction = runtime_inputs.partial_whole_cluster_fraction
                if fraction is None:
                    applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Partial whole-cluster selection requires an explicit fraction; no fraction is inferred from the label."))
                else:
                    current_plan = replace(
                        current_plan,
                        alcoholic_params=replace(p, whole_cluster_fraction=fraction),
                    )
                    applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied explicit whole-cluster fraction {fraction:g}."))
            continue

        if decision.id == "oxygen-fermentation":
            prior = OXYGEN_MANAGEMENT_PRIORS.get(option.id)
            if prior is None:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "runtime_not_implemented", "No oxygen-management prior exists for this option."))
            else:
                p = current_plan.alcoholic_params
                current_plan = replace(
                    current_plan,
                    alcoholic_params=replace(p, oxygen_management_index=prior),
                )
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied derived simulator oxygen-management prior {prior:g}."))
            continue

        if decision.id == "mlf":
            if option.id == "blocked":
                current_plan = replace(current_plan, malolactic=False)
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", "Disabled malolactic fermentation."))
            elif option.id == "complete":
                current_plan = replace(current_plan, malolactic=True)
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", "Enabled the current complete-MLF engine."))
            else:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "runtime_not_implemented", "The current MLF engine is binary and cannot represent a controlled partial MLF without a target-malate state."))
            continue

        if decision.id == "filtration":
            if option.id == "sterile":
                current_plan = replace(current_plan, sterile_packaging=True)
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", "Enabled sterile-packaging credit in the process model."))
            else:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "matrix_only", "No sterile-packaging credit is inferred from this filtration choice."))
            continue

        if decision.id == "white-juice-turbidity":
            if runtime_inputs.juice_turbidity_ntu is None:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Juice-solids risk requires an explicit NTU measurement; the qualitative option does not create one."))
            else:
                current_must = replace(current_must, juice_turbidity_ntu=runtime_inputs.juice_turbidity_ntu)
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied measured juice turbidity {runtime_inputs.juice_turbidity_ntu:g} NTU."))
            continue

        if decision.id == "bottling-oxygen":
            if runtime_inputs.prebottling_dissolved_oxygen_mg_l is None:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Pre-bottling dissolved oxygen must be measured; no mg/L value is inferred from a qualitative oxygen-control option."))
            else:
                current_packaging = replace(
                    current_packaging,
                    prebottling_dissolved_oxygen_mg_l=runtime_inputs.prebottling_dissolved_oxygen_mg_l,
                )
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied measured dissolved oxygen {runtime_inputs.prebottling_dissolved_oxygen_mg_l:g} mg/L."))
            continue

        if decision.id == "closure":
            if runtime_inputs.closure_oxygen_exposure_prior is None:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Closure oxygen behavior requires an explicit exposure prior; no OTR is inferred from the option or closure name."))
            else:
                current_packaging = replace(
                    current_packaging,
                    closure_oxygen_exposure_prior=runtime_inputs.closure_oxygen_exposure_prior,
                )
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied explicit closure oxygen-exposure prior {runtime_inputs.closure_oxygen_exposure_prior:g}."))
            continue

        applications.append(
            DecisionRuntimeApplication(
                decision.id,
                option.id,
                "matrix_only",
                "The selection contributes its bounded decision-matrix prior but has no mechanical runtime mapping yet.",
            )
        )

    return DecisionRuntimeResult(
        must=current_must,
        fermentation_plan=current_plan,
        packaging_plan=current_packaging,
        axis_effects=MappingProxyType(axis_effects),
        applications=tuple(applications),
    )
