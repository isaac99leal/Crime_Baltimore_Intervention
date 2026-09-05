"""Validated fermentation orchestration for Sommelier Simulator v2.

This module wraps the lower-level hourly alcoholic-fermentation and daily MLF
models with hard input bounds and explicit process plans. It prevents chemically
nonsensical states such as negative sugar, impossible target residual sugar, or a
sweet-wine target with no arrest mechanism.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from .fermentation_engine import (
    AlcoholicFermentationParams,
    FermentationState,
    MalolacticParams,
    MalolacticState,
    initial_state,
    step_alcoholic_fermentation,
    step_malolactic,
)


class FermentationConstraintError(ValueError):
    """Raised when a fermentation plan requests an impossible process."""


@dataclass(frozen=True)
class MustComposition:
    volume_l: float
    sugar_g_l: float
    yan_mg_l: float
    ph: float
    titratable_acidity_g_l: float
    malic_acid_g_l: float
    tartaric_acid_g_l: float = 3.0
    temp_c: float = 18.0
    initial_ethanol_pct: float = 0.0
    initial_biomass_g_l: float = 0.12
    free_so2_mg_l: float = 5.0
    volatile_acidity_g_l: float = 0.20
    solids_pct: float = 2.0
    botrytis_fraction: float = 0.0
    rot_fraction: float = 0.0


@dataclass(frozen=True)
class NutrientAddition:
    hour: float
    yan_mg_l: float
    kind: str = "organic_or_inorganic_nutrient"


@dataclass(frozen=True)
class FermentationPlan:
    style: str = "red"
    target_residual_sugar_g_l: float = 2.0
    arrest_method: str | None = None
    max_hours: float = 720.0
    dt_hours: float = 1.0
    inoculation_mode: str = "inoculated"
    allow_native_stall: bool = False
    nutrient_additions: tuple[NutrientAddition, ...] = ()
    alcoholic_params: AlcoholicFermentationParams = field(default_factory=AlcoholicFermentationParams)

    malolactic: bool = False
    malolactic_params: MalolacticParams = field(default_factory=MalolacticParams)
    mlf_max_days: float = 120.0
    mlf_start_temp_c: float = 20.0


@dataclass(frozen=True)
class FermentationResult:
    status: str
    alcoholic_history: tuple[FermentationState, ...]
    malolactic_history: tuple[MalolacticState, ...]
    final_sugar_g_l: float
    final_ethanol_pct: float
    final_yan_mg_l: float
    final_temp_c: float
    final_volatile_acidity_g_l: float
    final_malic_acid_g_l: float
    final_lactic_acid_g_l: float
    arrested: bool
    dry: bool
    alcoholic_completed: bool
    malolactic_completed: bool
    stuck: bool
    warnings: tuple[str, ...] = ()


ALLOWED_ARREST_METHODS = {
    "chill_and_sterile_filter",
    "sterile_filter",
    "fortification",
    "chill_and_sulfur",
    "centrifuge_and_sterile_filter",
}


def _bounded(name: str, value: float, low: float, high: float) -> None:
    if not low <= value <= high:
        raise FermentationConstraintError(f"{name} must be within {low}..{high}; got {value}")


def validate_must(must: MustComposition) -> None:
    _bounded("volume_l", must.volume_l, 0.1, 10_000_000.0)
    _bounded("sugar_g_l", must.sugar_g_l, 0.0, 650.0)
    _bounded("yan_mg_l", must.yan_mg_l, 0.0, 1200.0)
    _bounded("pH", must.ph, 2.0, 5.0)
    _bounded("titratable_acidity_g_l", must.titratable_acidity_g_l, 0.1, 30.0)
    _bounded("malic_acid_g_l", must.malic_acid_g_l, 0.0, 20.0)
    _bounded("tartaric_acid_g_l", must.tartaric_acid_g_l, 0.0, 20.0)
    _bounded("temp_c", must.temp_c, -5.0, 55.0)
    _bounded("initial_ethanol_pct", must.initial_ethanol_pct, 0.0, 25.0)
    _bounded("initial_biomass_g_l", must.initial_biomass_g_l, 0.001, 20.0)
    _bounded("free_so2_mg_l", must.free_so2_mg_l, 0.0, 300.0)
    _bounded("volatile_acidity_g_l", must.volatile_acidity_g_l, 0.0, 10.0)
    _bounded("solids_pct", must.solids_pct, 0.0, 60.0)
    _bounded("botrytis_fraction", must.botrytis_fraction, 0.0, 1.0)
    _bounded("rot_fraction", must.rot_fraction, 0.0, 1.0)


def validate_plan(must: MustComposition, plan: FermentationPlan) -> None:
    validate_must(must)
    target = plan.target_residual_sugar_g_l
    _bounded("target_residual_sugar_g_l", target, 0.0, must.sugar_g_l)
    _bounded("max_hours", plan.max_hours, 1.0, 3000.0)
    _bounded("dt_hours", plan.dt_hours, 0.05, 24.0)
    if plan.style not in {"red", "white", "rosé", "rose", "orange", "sparkling_base"}:
        raise FermentationConstraintError(f"Unsupported fermentation style {plan.style!r}")
    if target > 2.0 and not plan.arrest_method:
        raise FermentationConstraintError("A planned residual sugar above 2 g/L requires an explicit arrest method.")
    if plan.arrest_method and plan.arrest_method not in ALLOWED_ARREST_METHODS:
        raise FermentationConstraintError(f"Unsupported arrest method {plan.arrest_method!r}")
    if plan.malolactic and plan.arrest_method in {"sterile_filter", "chill_and_sterile_filter", "centrifuge_and_sterile_filter"}:
        raise FermentationConstraintError("MLF cannot be scheduled after a process that sterile-filters the wine.")
    if plan.mlf_max_days <= 0 or plan.mlf_max_days > 365:
        raise FermentationConstraintError("mlf_max_days must be >0 and <=365")

    total_nutrient = 0.0
    for addition in plan.nutrient_additions:
        _bounded("nutrient addition hour", addition.hour, 0.0, plan.max_hours)
        _bounded("nutrient YAN addition", addition.yan_mg_l, 0.0, 300.0)
        total_nutrient += addition.yan_mg_l
    if total_nutrient > 600.0:
        raise FermentationConstraintError("Total modeled nutrient addition above 600 mg/L YAN is outside the supported process envelope.")

    p = plan.alcoholic_params
    if not (p.minimum_active_temp_c < p.optimum_temp_c < p.maximum_active_temp_c):
        raise FermentationConstraintError("Fermentation temperature bounds must satisfy minimum < optimum < maximum.")
    _bounded("vessel_pressure_retention", p.vessel_pressure_retention, 0.0, 1.0)
    _bounded("oxygen_management_index", p.oxygen_management_index, 0.0, 1.0)
    _bounded("whole_cluster_fraction", p.whole_cluster_fraction, 0.0, 1.0)
    if p.sugar_g_l_per_abv_pct <= 10 or p.sugar_g_l_per_abv_pct >= 30:
        raise FermentationConstraintError("Sugar-to-ethanol conversion must remain within 10..30 g/L sugar per %ABV.")


def _planned_params(plan: FermentationPlan) -> AlcoholicFermentationParams:
    p = plan.alcoholic_params
    return p if p.style == plan.style else replace(p, style=plan.style)


def _apply_due_nutrients(state: FermentationState, additions: tuple[NutrientAddition, ...], applied: set[int]) -> FermentationState:
    yan = state.yan_mg_l
    changed = False
    for index, addition in enumerate(additions):
        if index in applied:
            continue
        if state.hour + 1e-9 >= addition.hour:
            yan += addition.yan_mg_l
            applied.add(index)
            changed = True
    return replace(state, yan_mg_l=yan) if changed else state


def _complete_to_target(state: FermentationState, target_sugar_g_l: float, params: AlcoholicFermentationParams) -> FermentationState:
    """Reconcile a small low-level finish tolerance to the process RS target.

    The low-level kinetic model can mark a batch ``finished`` a few hundredths
    of a gram per litre above the process-level dry target. Treating that state
    as incomplete created a state-machine contradiction. This function closes
    only that small remaining sugar mass and applies the same sugar→ethanol,
    YAN and CO2 stoichiometry used by the kinetic model.
    """
    target = max(0.0, target_sugar_g_l)
    consumed = max(0.0, state.sugar_g_l - target)
    if consumed > 0.10:
        raise FermentationConstraintError("Low-level fermentation stopped too far above the requested residual-sugar target.")
    return replace(
        state,
        sugar_g_l=target,
        ethanol_pct=state.ethanol_pct + consumed / params.sugar_g_l_per_abv_pct,
        yan_mg_l=max(0.0, state.yan_mg_l - consumed * params.yan_consumption_mg_per_g_sugar),
        co2_generated_g_l=state.co2_generated_g_l + consumed * params.co2_yield_g_per_g_sugar,
        finished=True,
    )


def run_fermentation(must: MustComposition, plan: FermentationPlan) -> FermentationResult:
    validate_plan(must, plan)
    params = _planned_params(plan)
    additions = tuple(sorted(plan.nutrient_additions, key=lambda a: a.hour))
    applied: set[int] = set()

    current = initial_state(
        sugar_g_l=must.sugar_g_l,
        yan_mg_l=must.yan_mg_l,
        temp_c=must.temp_c,
        biomass_g_l=must.initial_biomass_g_l,
        ethanol_pct=must.initial_ethanol_pct,
    )
    current = replace(current, volatile_acidity_g_l=must.volatile_acidity_g_l)
    history: list[FermentationState] = [current]
    arrested = False
    stuck = False
    warnings: list[str] = []

    while current.hour < plan.max_hours:
        current = _apply_due_nutrients(current, additions, applied)
        if current.sugar_g_l <= plan.target_residual_sugar_g_l + 0.05:
            current = _complete_to_target(current, plan.target_residual_sugar_g_l, params)
            arrested = plan.target_residual_sugar_g_l > 2.0
            history.append(current)
            break

        next_state = step_alcoholic_fermentation(current, params, dt_hours=min(plan.dt_hours, plan.max_hours - current.hour))

        if plan.target_residual_sugar_g_l > 2.0 and next_state.sugar_g_l < plan.target_residual_sugar_g_l:
            consumed = max(0.0, current.sugar_g_l - plan.target_residual_sugar_g_l)
            denominator = current.sugar_g_l - next_state.sugar_g_l
            fraction = consumed / max(1e-12, denominator) if denominator else 0.0
            fraction = max(0.0, min(1.0, fraction))
            next_state = replace(
                next_state,
                hour=current.hour + plan.dt_hours * fraction,
                sugar_g_l=plan.target_residual_sugar_g_l,
                ethanol_pct=current.ethanol_pct + (next_state.ethanol_pct - current.ethanol_pct) * fraction,
                yan_mg_l=current.yan_mg_l + (next_state.yan_mg_l - current.yan_mg_l) * fraction,
                co2_generated_g_l=current.co2_generated_g_l + (next_state.co2_generated_g_l - current.co2_generated_g_l) * fraction,
                finished=True,
            )
            arrested = True

        history.append(next_state)
        current = next_state
        if arrested:
            break
        if current.finished:
            if current.sugar_g_l <= plan.target_residual_sugar_g_l + 0.05:
                current = _complete_to_target(current, plan.target_residual_sugar_g_l, params)
                history[-1] = current
            else:
                warnings.append("The kinetic model stopped above the requested residual-sugar target.")
            break

        if len(history) > 36:
            prior = history[-25]
            progress = prior.sugar_g_l - current.sugar_g_l
            if progress < 0.05 and current.stuck_risk >= 0.85:
                stuck = True
                warnings.append(f"Alcoholic fermentation stalled with {current.sugar_g_l:.1f} g/L residual sugar.")
                break

    if current.hour >= plan.max_hours and not current.finished:
        stuck = True
        warnings.append("Alcoholic fermentation reached the configured time limit.")

    dry = current.sugar_g_l <= 2.0 + 1e-9
    alcoholic_completed = dry or arrested
    if stuck and plan.allow_native_stall:
        warnings.append("The plan allows a natural stall; wine remains microbiologically unstable.")
    elif stuck and not plan.allow_native_stall:
        warnings.append("Stuck fermentation requires a cellar intervention before release.")

    mlf_history: list[MalolacticState] = []
    final_malic = must.malic_acid_g_l
    final_lactic = 0.0
    mlf_completed = False

    if plan.malolactic:
        if not alcoholic_completed:
            warnings.append("MLF was not started because alcoholic fermentation did not complete.")
        elif must.malic_acid_g_l <= 0.10:
            mlf_completed = True
        else:
            mlf = MalolacticState(
                day=0.0,
                malic_g_l=must.malic_acid_g_l,
                lactic_g_l=0.0,
                ph=must.ph,
                temp_c=plan.mlf_start_temp_c,
                ethanol_pct=current.ethanol_pct,
                free_so2_mg_l=must.free_so2_mg_l,
                volatile_acidity_g_l=current.volatile_acidity_g_l,
            )
            mlf_history.append(mlf)
            while mlf.day < plan.mlf_max_days and not mlf.finished:
                mlf = step_malolactic(mlf, plan.malolactic_params, dt_days=1.0)
                mlf_history.append(mlf)
                if len(mlf_history) > 15:
                    prior = mlf_history[-8]
                    if prior.malic_g_l - mlf.malic_g_l < 0.002 and mlf.stalled_risk > 0.85:
                        warnings.append(f"MLF stalled with {mlf.malic_g_l:.2f} g/L malic acid.")
                        break
            final_malic = mlf.malic_g_l
            final_lactic = mlf.lactic_g_l
            mlf_completed = mlf.finished

    status = "stuck" if stuck else "arrested" if arrested else "dry_complete" if dry else "incomplete"
    if plan.malolactic and alcoholic_completed:
        status += "_mlf_complete" if mlf_completed else "_mlf_incomplete"

    final_va = mlf_history[-1].volatile_acidity_g_l if mlf_history else current.volatile_acidity_g_l
    return FermentationResult(
        status=status,
        alcoholic_history=tuple(history),
        malolactic_history=tuple(mlf_history),
        final_sugar_g_l=max(0.0, current.sugar_g_l),
        final_ethanol_pct=max(0.0, current.ethanol_pct),
        final_yan_mg_l=max(0.0, current.yan_mg_l),
        final_temp_c=current.temp_c,
        final_volatile_acidity_g_l=max(0.0, final_va),
        final_malic_acid_g_l=max(0.0, final_malic),
        final_lactic_acid_g_l=max(0.0, final_lactic),
        arrested=arrested,
        dry=dry,
        alcoholic_completed=alcoholic_completed,
        malolactic_completed=mlf_completed,
        stuck=stuck,
        warnings=tuple(warnings),
    )
