"""Explicit cellar maturation / élevage mechanics.

This layer models post-fermentation, pre-bottling evolution separately from
bottle aging. It can represent oxygen transfer, ullage and topping, deliberate
oxygen additions, oak contact, lees contact, and bâtonnage against an explicit
calendar.

No vessel, oak, or cellar-practice name creates a physical coefficient. Oxygen
transfer, oak extraction strength, event timing, and similar values must be
provided explicitly. Numeric transforms in this file are bounded simulator
priors, not published treatment coefficients.
"""
from __future__ import annotations

from dataclasses import dataclass


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class MaturationConstraintError(ValueError):
    """Raised when maturation inputs contain an invalid physical state."""


@dataclass(frozen=True)
class MaturationInput:
    ph: float
    free_so2_mg_l: float
    tannin_index: float = 0.0
    phenolic_index: float = 0.0
    anthocyanin_index: float = 0.0
    microbial_risk: float = 0.0
    dissolved_oxygen_mg_l: float | None = None

    def __post_init__(self) -> None:
        if not 2.0 <= self.ph <= 5.0:
            raise MaturationConstraintError("pH must be within 2..5")
        if not 0.0 <= self.free_so2_mg_l <= 300.0:
            raise MaturationConstraintError("free_so2_mg_l must be within 0..300")
        for name, value in (
            ("tannin_index", self.tannin_index),
            ("phenolic_index", self.phenolic_index),
            ("anthocyanin_index", self.anthocyanin_index),
            ("microbial_risk", self.microbial_risk),
        ):
            if not 0.0 <= value <= 1.0:
                raise MaturationConstraintError(f"{name} must be within 0..1")
        if self.dissolved_oxygen_mg_l is not None and not 0.0 <= self.dissolved_oxygen_mg_l <= 20.0:
            raise MaturationConstraintError("dissolved_oxygen_mg_l must be within 0..20")


@dataclass(frozen=True)
class BatonnageEvent:
    day: float
    intensity: float

    def __post_init__(self) -> None:
        if self.day < 0.0:
            raise MaturationConstraintError("Bâtonnage day must be non-negative")
        if not 0.0 <= self.intensity <= 1.0:
            raise MaturationConstraintError("Bâtonnage intensity must be within 0..1")


@dataclass(frozen=True)
class ToppingEvent:
    day: float
    ullage_reduction_fraction: float

    def __post_init__(self) -> None:
        if self.day < 0.0:
            raise MaturationConstraintError("Topping day must be non-negative")
        if not 0.0 <= self.ullage_reduction_fraction <= 1.0:
            raise MaturationConstraintError("ullage_reduction_fraction must be within 0..1")


@dataclass(frozen=True)
class OxygenAddition:
    day: float
    oxygen_mg_l: float

    def __post_init__(self) -> None:
        if self.day < 0.0:
            raise MaturationConstraintError("Oxygen-addition day must be non-negative")
        if not 0.0 <= self.oxygen_mg_l <= 20.0:
            raise MaturationConstraintError("oxygen_mg_l must be within 0..20")


@dataclass(frozen=True)
class MaturationPlan:
    duration_days: float
    step_days: float = 1.0
    vessel_label: str = "unspecified"
    vessel_oxygen_transfer_mg_l_month: float | None = None
    headspace_oxygen_exposure_mg_l_month: float | None = None
    evaporation_fraction_per_month: float = 0.0
    oak_contact_fraction: float = 0.0
    oak_extraction_prior: float = 0.0
    oak_context_labels: tuple[str, ...] = ()
    lees_contact_until_day: float | None = None
    batonnage_events: tuple[BatonnageEvent, ...] = ()
    topping_events: tuple[ToppingEvent, ...] = ()
    oxygen_additions: tuple[OxygenAddition, ...] = ()
    # Explicit simulator priors controlling reaction bookkeeping. They are not
    # asserted as universal chemical constants.
    oxygen_reaction_fraction_per_day: float = 0.35
    so2_consumption_prior_mg_per_mg_oxygen: float = 1.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.duration_days <= 20_000.0:
            raise MaturationConstraintError("duration_days must be within 0..20000")
        if not 0.05 <= self.step_days <= 31.0:
            raise MaturationConstraintError("step_days must be within 0.05..31")
        if not self.vessel_label.strip():
            raise MaturationConstraintError("vessel_label cannot be blank")
        for name, value, high in (
            ("vessel_oxygen_transfer_mg_l_month", self.vessel_oxygen_transfer_mg_l_month, 20.0),
            ("headspace_oxygen_exposure_mg_l_month", self.headspace_oxygen_exposure_mg_l_month, 20.0),
        ):
            if value is not None and not 0.0 <= value <= high:
                raise MaturationConstraintError(f"{name} must be within 0..{high:g}")
        if not 0.0 <= self.evaporation_fraction_per_month <= 0.25:
            raise MaturationConstraintError("evaporation_fraction_per_month must be within 0..0.25")
        if not 0.0 <= self.oak_contact_fraction <= 1.0:
            raise MaturationConstraintError("oak_contact_fraction must be within 0..1")
        if not 0.0 <= self.oak_extraction_prior <= 1.0:
            raise MaturationConstraintError("oak_extraction_prior must be within 0..1")
        if self.lees_contact_until_day is not None and not 0.0 <= self.lees_contact_until_day <= self.duration_days:
            raise MaturationConstraintError("lees_contact_until_day must fall within the maturation duration")
        if not 0.0 <= self.oxygen_reaction_fraction_per_day <= 1.0:
            raise MaturationConstraintError("oxygen_reaction_fraction_per_day must be within 0..1")
        if not 0.0 <= self.so2_consumption_prior_mg_per_mg_oxygen <= 20.0:
            raise MaturationConstraintError("so2_consumption_prior_mg_per_mg_oxygen must be within 0..20")
        for events, label in (
            (self.batonnage_events, "batonnage_events"),
            (self.topping_events, "topping_events"),
            (self.oxygen_additions, "oxygen_additions"),
        ):
            prior = -1.0
            for event in events:
                if event.day < prior:
                    raise MaturationConstraintError(f"{label} must be ordered by day")
                if event.day > self.duration_days + 1e-9:
                    raise MaturationConstraintError(f"{label} cannot contain events after duration_days")
                prior = event.day


@dataclass(frozen=True)
class MaturationState:
    day: float
    free_so2_mg_l: float
    tannin_index: float
    phenolic_index: float
    anthocyanin_index: float
    polymerized_tannin_index: float
    oak_compound_index: float
    lees_autolysis_index: float
    microbial_risk: float
    ullage_fraction: float
    dissolved_oxygen_mg_l: float | None
    cumulative_oxygen_input_mg_l: float | None
    oxidative_development: float | None
    reductive_risk: float | None


@dataclass(frozen=True)
class MaturationResult:
    final_state: MaturationState
    history: tuple[MaturationState, ...]
    oxygen_model_complete: bool
    batonnage_event_count: int
    topping_event_count: int
    oxygen_addition_count: int
    warnings: tuple[str, ...] = ()


def _events_in_interval(events: tuple[object, ...], start: float, end: float, duration: float) -> tuple[object, ...]:
    selected: list[object] = []
    for event in events:
        day = float(getattr(event, "day"))
        in_interval = start <= day < end
        if abs(end - duration) <= 1e-9 and abs(day - duration) <= 1e-9:
            in_interval = True
        if in_interval:
            selected.append(event)
    return tuple(selected)


def simulate_maturation(
    initial: MaturationInput,
    plan: MaturationPlan,
) -> MaturationResult:
    """Simulate an explicit pre-bottling maturation plan."""
    oxygen_complete = (
        initial.dissolved_oxygen_mg_l is not None
        and plan.vessel_oxygen_transfer_mg_l_month is not None
        and plan.headspace_oxygen_exposure_mg_l_month is not None
    )
    warnings: list[str] = []
    if not oxygen_complete and plan.duration_days > 0.0:
        warnings.append(
            "Oxygen evolution is unresolved because initial dissolved oxygen, vessel oxygen transfer, "
            "and headspace oxygen exposure were not all supplied explicitly."
        )

    state = MaturationState(
        day=0.0,
        free_so2_mg_l=initial.free_so2_mg_l,
        tannin_index=initial.tannin_index,
        phenolic_index=initial.phenolic_index,
        anthocyanin_index=initial.anthocyanin_index,
        polymerized_tannin_index=0.0,
        oak_compound_index=0.0,
        lees_autolysis_index=0.0,
        microbial_risk=initial.microbial_risk,
        ullage_fraction=0.0,
        dissolved_oxygen_mg_l=initial.dissolved_oxygen_mg_l if oxygen_complete else None,
        cumulative_oxygen_input_mg_l=0.0 if oxygen_complete else None,
        oxidative_development=0.0 if oxygen_complete else None,
        reductive_risk=0.0 if oxygen_complete else None,
    )
    history: list[MaturationState] = [state]
    batonnage_count = 0
    topping_count = 0
    oxygen_addition_count = 0

    while state.day < plan.duration_days - 1e-9:
        end_day = min(plan.duration_days, state.day + plan.step_days)
        dt = end_day - state.day
        month_fraction = dt / 30.4375
        batonnage = _events_in_interval(plan.batonnage_events, state.day, end_day, plan.duration_days)
        topping = _events_in_interval(plan.topping_events, state.day, end_day, plan.duration_days)
        oxygen_events = _events_in_interval(plan.oxygen_additions, state.day, end_day, plan.duration_days)
        batonnage_count += len(batonnage)
        topping_count += len(topping)
        oxygen_addition_count += len(oxygen_events)

        ullage = _clamp(
            state.ullage_fraction + plan.evaporation_fraction_per_month * month_fraction
        )
        for event in topping:
            assert isinstance(event, ToppingEvent)
            ullage *= 1.0 - event.ullage_reduction_fraction
        ullage = _clamp(ullage)

        lees_active_days = 0.0
        if plan.lees_contact_until_day is not None:
            lees_active_days = max(
                0.0,
                min(end_day, plan.lees_contact_until_day) - min(state.day, plan.lees_contact_until_day),
            )
        batonnage_load = sum(
            event.intensity for event in batonnage if isinstance(event, BatonnageEvent)
        )
        autolysis = _clamp(
            state.lees_autolysis_index
            + 0.0013 * lees_active_days * (1.0 - state.lees_autolysis_index)
            + 0.012 * batonnage_load * (1.0 - state.lees_autolysis_index)
        )

        oak_gain = (
            0.0022
            * dt
            * plan.oak_contact_fraction
            * plan.oak_extraction_prior
            * (1.0 - state.oak_compound_index)
        )
        oak = _clamp(state.oak_compound_index + oak_gain)

        dissolved_oxygen = state.dissolved_oxygen_mg_l
        cumulative_oxygen = state.cumulative_oxygen_input_mg_l
        oxidative = state.oxidative_development
        reductive = state.reductive_risk
        free_so2 = state.free_so2_mg_l
        reacted_oxygen = 0.0

        if oxygen_complete:
            assert dissolved_oxygen is not None
            assert cumulative_oxygen is not None
            assert oxidative is not None
            assert reductive is not None
            assert plan.vessel_oxygen_transfer_mg_l_month is not None
            assert plan.headspace_oxygen_exposure_mg_l_month is not None

            vessel_input = plan.vessel_oxygen_transfer_mg_l_month * month_fraction
            headspace_input = (
                plan.headspace_oxygen_exposure_mg_l_month
                * (0.10 + 0.90 * ullage)
                * month_fraction
            )
            deliberate_input = sum(
                event.oxygen_mg_l for event in oxygen_events if isinstance(event, OxygenAddition)
            )
            oxygen_input = vessel_input + headspace_input + deliberate_input
            cumulative_oxygen += oxygen_input
            dissolved_oxygen += oxygen_input
            reaction_fraction = 1.0 - (1.0 - plan.oxygen_reaction_fraction_per_day) ** dt
            reacted_oxygen = dissolved_oxygen * _clamp(reaction_fraction)
            dissolved_oxygen = max(0.0, dissolved_oxygen - reacted_oxygen)
            free_so2 = max(
                0.0,
                free_so2 - reacted_oxygen * plan.so2_consumption_prior_mg_per_mg_oxygen,
            )
            low_so2_pressure = _clamp((25.0 - free_so2) / 25.0)
            oxidative = _clamp(
                oxidative
                + 0.030 * reacted_oxygen * (0.55 + 0.45 * low_so2_pressure) * (1.0 - oxidative)
            )
            oxygen_relief = _clamp(oxygen_input / max(0.05, dt * 0.10))
            lees_pressure = 1.0 if lees_active_days > 0.0 else 0.0
            reductive = _clamp(
                reductive
                + month_fraction * (0.08 * lees_pressure - 0.10 * oxygen_relief)
            )

        polymer_gain = (
            (0.012 * reacted_oxygen if oxygen_complete else 0.0)
            + 0.00025 * dt * state.phenolic_index
        ) * (1.0 - state.polymerized_tannin_index)
        polymerized = _clamp(state.polymerized_tannin_index + polymer_gain)
        tannin = _clamp(state.tannin_index - 0.10 * polymer_gain)
        # A small fraction of free anthocyanin is moved out of the free pool as
        # polymerization proceeds. This is a simulator transform, not a mass assay.
        anthocyanin = _clamp(state.anthocyanin_index - 0.06 * polymer_gain)
        phenolic = state.phenolic_index

        ph_pressure = _clamp((initial.ph - 3.40) / 0.80)
        so2_protection = _clamp(free_so2 / 35.0)
        microbial = _clamp(
            state.microbial_risk
            + month_fraction * (
                0.055 * ph_pressure * (1.0 - so2_protection)
                + 0.045 * ullage
                - 0.035 * so2_protection
            )
        )

        state = MaturationState(
            day=end_day,
            free_so2_mg_l=free_so2,
            tannin_index=tannin,
            phenolic_index=phenolic,
            anthocyanin_index=anthocyanin,
            polymerized_tannin_index=polymerized,
            oak_compound_index=oak,
            lees_autolysis_index=autolysis,
            microbial_risk=microbial,
            ullage_fraction=ullage,
            dissolved_oxygen_mg_l=dissolved_oxygen,
            cumulative_oxygen_input_mg_l=cumulative_oxygen,
            oxidative_development=oxidative,
            reductive_risk=reductive,
        )
        history.append(state)

    return MaturationResult(
        final_state=state,
        history=tuple(history),
        oxygen_model_complete=oxygen_complete,
        batonnage_event_count=batonnage_count,
        topping_event_count=topping_count,
        oxygen_addition_count=oxygen_addition_count,
        warnings=tuple(warnings),
    )
