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

from .extraction_process import CapManagementEvent, ExtractionPlan
from .fermentation_process import FermentationPlan, MustComposition
from .legal_practice_bridge import LegalPracticeBridge
from .legal_specs import LegalWineSpec
from .maturation_process import BatonnageEvent, MaturationPlan, OxygenAddition, ToppingEvent
from .packaging import PackagingPlan
from .winemaking_decisions import WinemakingDecisionRegistry


class DecisionRuntimeError(ValueError):
    """Raised when a selected decision cannot be executed safely."""


@dataclass(frozen=True)
class DecisionRuntimeInputs:
    """Explicit measurements/priors required by qualitative decision labels."""

    partial_whole_cluster_fraction: float | None = None
    partial_mlf_target_malic_g_l: float | None = None
    fermentation_temperature_schedule: tuple[tuple[float, float], ...] = ()
    maceration_start_hour: float | None = None
    maceration_end_hour: float | None = None
    # Cap-management points are (hour, intensity). The selected decision option
    # supplies the method label; event frequency/intensity are never inferred.
    cap_management_events: tuple[tuple[float, float], ...] = ()
    press_wine_blend_fraction: float | None = None
    press_severity: float | None = None

    # Élevage inputs. Names never manufacture these physical values.
    maturation_duration_days: float | None = None
    vessel_oxygen_transfer_mg_l_month: float | None = None
    headspace_oxygen_exposure_mg_l_month: float | None = None
    evaporation_fraction_per_month: float | None = None
    oak_contact_fraction: float | None = None
    oak_extraction_prior: float | None = None
    lees_contact_until_day: float | None = None
    batonnage_events: tuple[tuple[float, float], ...] = ()
    topping_events: tuple[tuple[float, float], ...] = ()
    microoxygenation_additions: tuple[tuple[float, float], ...] = ()

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
    extraction_plan: ExtractionPlan = ExtractionPlan()
    maturation_plan: MaturationPlan = MaturationPlan(duration_days=0.0)

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

_OAK_NEW_PERCENTAGE_RANGES = MappingProxyType(
    {
        "zero": (0.0, 0.0),
        "low": (0.01, 0.25),
        "medium": (0.26, 0.60),
        "high": (0.61, 1.0),
    }
)


def _confirmation_key(decision_id: str, option_id: str) -> str:
    return f"{decision_id}:{option_id}"


def _validate_event_points(
    points: tuple[tuple[float, float], ...],
    *,
    name: str,
    second_high: float,
) -> None:
    prior = -1.0
    for point in points:
        if len(point) != 2:
            raise DecisionRuntimeError(f"Each {name} point must contain exactly two values")
        day, second = float(point[0]), float(point[1])
        if day < 0.0 or day < prior:
            raise DecisionRuntimeError(f"{name} days must be non-negative and ordered")
        if not 0.0 <= second <= second_high:
            raise DecisionRuntimeError(f"{name} second value must be within 0..{second_high:g}")
        prior = day


def _validate_runtime_inputs(inputs: DecisionRuntimeInputs) -> None:
    if inputs.partial_whole_cluster_fraction is not None and not (
        0.0 < inputs.partial_whole_cluster_fraction < 1.0
    ):
        raise DecisionRuntimeError("partial_whole_cluster_fraction must be strictly between 0 and 1")
    if inputs.partial_mlf_target_malic_g_l is not None and not (
        0.0 <= inputs.partial_mlf_target_malic_g_l <= 20.0
    ):
        raise DecisionRuntimeError("partial_mlf_target_malic_g_l must be within 0..20")
    prior_hour = -1.0
    for point in inputs.fermentation_temperature_schedule:
        if len(point) != 2:
            raise DecisionRuntimeError("Each fermentation temperature point must be (hour, target_temp_c)")
        hour, target = float(point[0]), float(point[1])
        if hour < 0.0 or hour <= prior_hour:
            raise DecisionRuntimeError("Fermentation temperature schedule hours must be non-negative and strictly increasing")
        if not -5.0 <= target <= 55.0:
            raise DecisionRuntimeError("Fermentation temperature targets must be within -5..55 C")
        prior_hour = hour
    if inputs.maceration_start_hour is not None and inputs.maceration_start_hour < 0.0:
        raise DecisionRuntimeError("maceration_start_hour must be non-negative")
    if inputs.maceration_end_hour is not None and inputs.maceration_end_hour < 0.0:
        raise DecisionRuntimeError("maceration_end_hour must be non-negative")
    if (
        inputs.maceration_start_hour is not None
        and inputs.maceration_end_hour is not None
        and inputs.maceration_end_hour < inputs.maceration_start_hour
    ):
        raise DecisionRuntimeError("maceration_end_hour cannot precede maceration_start_hour")
    _validate_event_points(inputs.cap_management_events, name="cap-management", second_high=1.0)
    if inputs.press_wine_blend_fraction is not None and not (
        0.0 <= inputs.press_wine_blend_fraction <= 1.0
    ):
        raise DecisionRuntimeError("press_wine_blend_fraction must be within 0..1")
    if inputs.press_severity is not None and not 0.0 <= inputs.press_severity <= 1.0:
        raise DecisionRuntimeError("press_severity must be within 0..1")

    if inputs.maturation_duration_days is not None and not 0.0 <= inputs.maturation_duration_days <= 20_000.0:
        raise DecisionRuntimeError("maturation_duration_days must be within 0..20000")
    for name, value, high in (
        ("vessel_oxygen_transfer_mg_l_month", inputs.vessel_oxygen_transfer_mg_l_month, 20.0),
        ("headspace_oxygen_exposure_mg_l_month", inputs.headspace_oxygen_exposure_mg_l_month, 20.0),
        ("evaporation_fraction_per_month", inputs.evaporation_fraction_per_month, 0.25),
        ("oak_contact_fraction", inputs.oak_contact_fraction, 1.0),
        ("oak_extraction_prior", inputs.oak_extraction_prior, 1.0),
    ):
        if value is not None and not 0.0 <= value <= high:
            raise DecisionRuntimeError(f"{name} must be within 0..{high:g}")
    if inputs.lees_contact_until_day is not None and inputs.lees_contact_until_day < 0.0:
        raise DecisionRuntimeError("lees_contact_until_day must be non-negative")
    _validate_event_points(inputs.batonnage_events, name="bâtonnage", second_high=1.0)
    _validate_event_points(inputs.topping_events, name="topping", second_high=1.0)
    _validate_event_points(inputs.microoxygenation_additions, name="micro-oxygenation", second_high=20.0)

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


def _maturation_seed(
    plan: MaturationPlan,
    inputs: DecisionRuntimeInputs,
) -> tuple[dict[str, object], list[str]]:
    values: dict[str, object] = {
        "duration_days": plan.duration_days,
        "step_days": plan.step_days,
        "vessel_label": plan.vessel_label,
        "vessel_oxygen_transfer_mg_l_month": plan.vessel_oxygen_transfer_mg_l_month,
        "headspace_oxygen_exposure_mg_l_month": plan.headspace_oxygen_exposure_mg_l_month,
        "evaporation_fraction_per_month": plan.evaporation_fraction_per_month,
        "oak_contact_fraction": plan.oak_contact_fraction,
        "oak_extraction_prior": plan.oak_extraction_prior,
        "oak_context_labels": plan.oak_context_labels,
        "lees_contact_until_day": plan.lees_contact_until_day,
        "batonnage_events": plan.batonnage_events,
        "topping_events": plan.topping_events,
        "oxygen_additions": plan.oxygen_additions,
        "oxygen_reaction_fraction_per_day": plan.oxygen_reaction_fraction_per_day,
        "so2_consumption_prior_mg_per_mg_oxygen": plan.so2_consumption_prior_mg_per_mg_oxygen,
    }
    if inputs.maturation_duration_days is not None:
        values["duration_days"] = inputs.maturation_duration_days
    if inputs.vessel_oxygen_transfer_mg_l_month is not None:
        values["vessel_oxygen_transfer_mg_l_month"] = inputs.vessel_oxygen_transfer_mg_l_month
    if inputs.headspace_oxygen_exposure_mg_l_month is not None:
        values["headspace_oxygen_exposure_mg_l_month"] = inputs.headspace_oxygen_exposure_mg_l_month
    if inputs.evaporation_fraction_per_month is not None:
        values["evaporation_fraction_per_month"] = inputs.evaporation_fraction_per_month
    if inputs.oak_contact_fraction is not None:
        values["oak_contact_fraction"] = inputs.oak_contact_fraction
    if inputs.oak_extraction_prior is not None:
        values["oak_extraction_prior"] = inputs.oak_extraction_prior
    if inputs.lees_contact_until_day is not None:
        values["lees_contact_until_day"] = inputs.lees_contact_until_day
    if inputs.batonnage_events:
        values["batonnage_events"] = tuple(
            BatonnageEvent(day=float(day), intensity=float(intensity))
            for day, intensity in inputs.batonnage_events
        )
    if inputs.topping_events:
        values["topping_events"] = tuple(
            ToppingEvent(day=float(day), ullage_reduction_fraction=float(fraction))
            for day, fraction in inputs.topping_events
        )
    if inputs.microoxygenation_additions:
        values["oxygen_additions"] = tuple(
            OxygenAddition(day=float(day), oxygen_mg_l=float(oxygen))
            for day, oxygen in inputs.microoxygenation_additions
        )
    return values, list(plan.oak_context_labels)


def apply_winemaking_decisions(
    selections: Mapping[str, str],
    *,
    must: MustComposition,
    fermentation_plan: FermentationPlan,
    packaging_plan: PackagingPlan = PackagingPlan(),
    extraction_plan: ExtractionPlan = ExtractionPlan(),
    maturation_plan: MaturationPlan = MaturationPlan(duration_days=0.0),
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
    current_extraction = extraction_plan
    maturation_values, oak_context_labels = _maturation_seed(maturation_plan, runtime_inputs)
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

        if decision.id == "fermentation-temperature-trajectory":
            schedule = runtime_inputs.fermentation_temperature_schedule
            if not schedule:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "A temperature-trajectory choice requires explicit time/temperature control points; no schedule is inferred from the qualitative label."))
            else:
                p = current_plan.alcoholic_params
                current_plan = replace(
                    current_plan,
                    alcoholic_params=replace(p, temperature_schedule=tuple(schedule)),
                )
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied {len(schedule)} explicit fermentation temperature control point(s)."))
            continue

        if decision.id == "cap-management":
            points = runtime_inputs.cap_management_events
            if not points:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Cap-management selection requires explicit event hours and intensities; frequency and force are not inferred from the method label."))
            else:
                events = tuple(
                    CapManagementEvent(hour=float(hour), intensity=float(intensity), method=option.id)
                    for hour, intensity in points
                )
                current_extraction = replace(current_extraction, cap_management_events=events)
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied {len(events)} explicit {option.id} cap-management event(s)."))
            continue

        if decision.id == "maceration-duration":
            end_hour = runtime_inputs.maceration_end_hour
            if end_hour is None:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Maceration duration requires an explicit skin-contact end hour; no duration is inferred from short/standard/extended labels."))
            else:
                start_hour = 0.0 if runtime_inputs.maceration_start_hour is None else runtime_inputs.maceration_start_hour
                current_extraction = replace(
                    current_extraction,
                    maceration_start_hour=start_hour,
                    maceration_end_hour=end_hour,
                )
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied explicit skin-contact window {start_hour:g} to {end_hour:g} fermentation hour(s)."))
            continue

        if decision.id == "press-fraction":
            blend_fraction = runtime_inputs.press_wine_blend_fraction
            severity = runtime_inputs.press_severity
            if blend_fraction is None or severity is None:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Press-fraction selection requires explicit press-wine blend fraction and press-severity inputs; neither is inferred from the qualitative option."))
            else:
                current_extraction = replace(
                    current_extraction,
                    press_wine_blend_fraction=blend_fraction,
                    press_severity=severity,
                )
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied explicit press-wine blend fraction {blend_fraction:g} and severity {severity:g}."))
            continue

        if decision.id == "mlf":
            if option.id == "blocked":
                current_plan = replace(current_plan, malolactic=False)
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", "Disabled malolactic fermentation."))
            elif option.id == "complete":
                current_plan = replace(
                    current_plan,
                    malolactic=True,
                    malolactic_params=replace(current_plan.malolactic_params, target_malic_g_l=0.10),
                )
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", "Enabled MLF with the complete-MLF target of 0.10 g/L malic acid."))
            else:
                target = runtime_inputs.partial_mlf_target_malic_g_l
                if target is None:
                    applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Partial MLF requires an explicit target malic-acid concentration; no percentage is inferred from the word partial."))
                elif not 0.10 < target < current_must.malic_acid_g_l:
                    raise DecisionRuntimeError(
                        "partial_mlf_target_malic_g_l must be >0.10 g/L and below the must's initial malic acid"
                    )
                else:
                    current_plan = replace(
                        current_plan,
                        malolactic=True,
                        malolactic_params=replace(current_plan.malolactic_params, target_malic_g_l=target),
                    )
                    applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Enabled partial MLF to explicit target {target:g} g/L malic acid."))
            continue

        if decision.id == "maturation-duration":
            if runtime_inputs.maturation_duration_days is None:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Maturation duration requires an explicit number of days; short/moderate/long does not create one."))
            else:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied explicit maturation duration {runtime_inputs.maturation_duration_days:g} days."))
            continue

        if decision.id == "maturation-vessel":
            maturation_values["vessel_label"] = option.id
            if runtime_inputs.vessel_oxygen_transfer_mg_l_month is None:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Vessel identity is recorded, but no oxygen-transfer value is inferred from the vessel label."))
            else:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Recorded vessel {option.id} with explicit oxygen transfer {runtime_inputs.vessel_oxygen_transfer_mg_l_month:g} mg/L/month."))
            continue

        if decision.id == "lees-contact":
            if option.id == "none":
                maturation_values["lees_contact_until_day"] = 0.0
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", "Set lees-contact endpoint to day 0."))
            elif runtime_inputs.lees_contact_until_day is None:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Lees-contact selection requires an explicit endpoint in days; short/extended does not create a duration."))
            else:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied explicit lees-contact endpoint day {runtime_inputs.lees_contact_until_day:g}."))
            continue

        if decision.id == "batonnage":
            if option.id == "none":
                maturation_values["batonnage_events"] = ()
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", "Cleared scheduled bâtonnage events."))
            elif not runtime_inputs.batonnage_events:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Bâtonnage selection requires explicit event days and intensities; frequency is not inferred from occasional/frequent."))
            else:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied {len(runtime_inputs.batonnage_events)} explicit bâtonnage event(s)."))
            continue

        if decision.id == "oak-new-percentage":
            if option.id == "zero":
                maturation_values["oak_contact_fraction"] = 0.0
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", "Set new-oak contact fraction to 0."))
            else:
                fraction = runtime_inputs.oak_contact_fraction
                if fraction is None:
                    applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "New-oak category requires an explicit fraction; the category range is not collapsed to a midpoint."))
                else:
                    low, high = _OAK_NEW_PERCENTAGE_RANGES[option.id]
                    if not low <= fraction <= high:
                        raise DecisionRuntimeError(
                            f"oak_contact_fraction {fraction:g} is outside the selected {option.id} range {low:g}..{high:g}"
                        )
                    applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied explicit oak-contact fraction {fraction:g} within selected {option.id} range."))
            continue

        if decision.id in {"oak-species", "oak-toast", "oak-age"}:
            oak_context_labels.append(f"{decision.id}:{option.id}")
            if runtime_inputs.oak_extraction_prior is None:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Oak context is recorded, but no extraction strength is inferred from species, toast, or barrel-age label."))
            else:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Recorded {decision.id}={option.id} with explicit oak-extraction prior {runtime_inputs.oak_extraction_prior:g}."))
            continue

        if decision.id == "topping-ullage":
            if runtime_inputs.headspace_oxygen_exposure_mg_l_month is None or runtime_inputs.evaporation_fraction_per_month is None:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Ullage strategy requires explicit headspace oxygen exposure and evaporation rate; neither is inferred from the strategy label."))
            elif option.id == "topped" and not runtime_inputs.topping_events:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "A topped strategy requires explicit topping event days and ullage-reduction fractions."))
            else:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied explicit ullage/oxygen inputs for {option.id} strategy."))
            continue

        if decision.id == "micro-oxygenation":
            if option.id == "none":
                maturation_values["oxygen_additions"] = ()
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", "Cleared deliberate maturation oxygen additions."))
            elif not runtime_inputs.microoxygenation_additions:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "requires_measurement", "Micro-oxygenation requires explicit event doses; low/higher does not generate mg/L oxygen."))
            else:
                applications.append(DecisionRuntimeApplication(decision.id, option.id, "applied", f"Applied {len(runtime_inputs.microoxygenation_additions)} explicit oxygen-addition event(s)."))
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

    maturation_values["oak_context_labels"] = tuple(dict.fromkeys(oak_context_labels))
    current_maturation = MaturationPlan(**maturation_values)

    return DecisionRuntimeResult(
        must=current_must,
        fermentation_plan=current_plan,
        packaging_plan=current_packaging,
        axis_effects=MappingProxyType(axis_effects),
        applications=tuple(applications),
        extraction_plan=current_extraction,
        maturation_plan=current_maturation,
    )
