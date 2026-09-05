"""Deterministic fermentation mechanics for Sommelier Simulator v2.

This module is a simulation model, not a laboratory prediction package. The
coefficients are explicit model priors. They are designed to preserve the main
causal relationships used in cellar decisions: temperature, assimilable nitrogen,
sugar, ethanol inhibition, yeast biomass, oxygen/closure state, extraction, and
malolactic constraints.

The model follows the dimensions used in OIV wine-yeast characterization
(fermentation kinetics across temperature, high-sugar must, nitrogen status,
volatile acidity, H2S and malic-acid behaviour) without claiming that one generic
curve represents every strain or must.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import exp


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class AlcoholicFermentationParams:
    style: str = "red"
    optimum_temp_c: float = 25.0
    minimum_active_temp_c: float = 10.0
    maximum_active_temp_c: float = 36.0
    max_sugar_rate_g_l_h: float = 1.35
    biomass_capacity_g_l: float = 1.6
    biomass_growth_per_h: float = 0.030
    sugar_g_l_per_abv_pct: float = 16.83
    yan_consumption_mg_per_g_sugar: float = 0.46
    co2_yield_g_per_g_sugar: float = 0.47
    heat_c_per_g_l_sugar: float = 0.018
    cooling_setpoint_c: float | None = 26.0
    cooling_strength_per_h: float = 0.22
    ambient_temp_c: float = 18.0
    ambient_exchange_per_h: float = 0.015
    vessel_pressure_retention: float = 0.0
    maceration: bool = True
    extraction_scale: float = 1.0
    whole_cluster_fraction: float = 0.0
    oxygen_management_index: float = 0.5


@dataclass(frozen=True)
class FermentationState:
    hour: float
    sugar_g_l: float
    ethanol_pct: float
    yan_mg_l: float
    temp_c: float
    biomass_g_l: float
    co2_generated_g_l: float = 0.0
    pressure_bar: float = 0.0
    volatile_acidity_g_l: float = 0.20
    h2s_risk: float = 0.0
    stuck_risk: float = 0.0
    anthocyanin_extraction: float = 0.0
    tannin_extraction: float = 0.0
    finished: bool = False


@dataclass(frozen=True)
class MalolacticParams:
    optimum_temp_c: float = 20.0
    optimum_ph: float = 3.45
    base_malic_rate_g_l_day: float = 0.35
    max_free_so2_mg_l: float = 30.0
    max_ethanol_pct: float = 16.0
    minimum_temp_c: float = 13.0
    maximum_temp_c: float = 27.0


@dataclass(frozen=True)
class MalolacticState:
    day: float
    malic_g_l: float
    lactic_g_l: float
    ph: float
    temp_c: float
    ethanol_pct: float
    free_so2_mg_l: float
    bacterial_activity: float = 0.2
    volatile_acidity_g_l: float = 0.25
    completion: float = 0.0
    stalled_risk: float = 0.0
    finished: bool = False


def initial_state(
    *,
    sugar_g_l: float = 220.0,
    yan_mg_l: float = 180.0,
    temp_c: float = 20.0,
    biomass_g_l: float = 0.12,
    ethanol_pct: float = 0.0,
) -> FermentationState:
    return FermentationState(
        hour=0.0,
        sugar_g_l=max(0.0, sugar_g_l),
        ethanol_pct=max(0.0, ethanol_pct),
        yan_mg_l=max(0.0, yan_mg_l),
        temp_c=temp_c,
        biomass_g_l=max(0.01, biomass_g_l),
    )


def temperature_activity(temp_c: float, params: AlcoholicFermentationParams) -> float:
    if temp_c <= params.minimum_active_temp_c or temp_c >= params.maximum_active_temp_c:
        return 0.02
    width = 7.5 if params.style == "white" else 8.5
    bell = exp(-((temp_c - params.optimum_temp_c) / width) ** 2)
    return clamp(bell, 0.02, 1.0)


def nitrogen_activity(yan_mg_l: float) -> float:
    # Smooth limitation. This avoids a fake binary threshold while still making
    # low-YAN must materially slower and more H2S/stuck-prone.
    return clamp(yan_mg_l / (yan_mg_l + 55.0), 0.05, 1.0)


def ethanol_activity(ethanol_pct: float) -> float:
    return clamp(1.0 - (max(0.0, ethanol_pct) / 17.2) ** 3, 0.03, 1.0)


def sugar_activity(sugar_g_l: float) -> float:
    return clamp(sugar_g_l / (sugar_g_l + 18.0), 0.02, 1.0)


def _risk_state(state: FermentationState, p: AlcoholicFermentationParams) -> tuple[float, float]:
    remaining = clamp(state.sugar_g_l / 220.0)
    low_n = clamp((110.0 - state.yan_mg_l) / 110.0)
    cold = clamp((14.0 - state.temp_c) / 6.0)
    hot = clamp((state.temp_c - 31.0) / 6.0)
    ethanol_pressure = clamp((state.ethanol_pct - 11.5) / 5.0)
    stalled = clamp(
        0.42 * low_n + 0.24 * cold + 0.28 * hot
        + 0.25 * ethanol_pressure * remaining
        + (0.18 if state.biomass_g_l < 0.10 and remaining > 0.1 else 0.0)
    )
    h2s = clamp(
        0.65 * low_n
        + 0.20 * clamp((16.0 - state.temp_c) / 8.0)
        + 0.15 * clamp(0.25 - p.oxygen_management_index, 0.0, 0.25) / 0.25
    )
    return stalled, h2s


def step_alcoholic_fermentation(
    state: FermentationState,
    params: AlcoholicFermentationParams = AlcoholicFermentationParams(),
    *,
    dt_hours: float = 1.0,
) -> FermentationState:
    if state.finished or dt_hours <= 0:
        return state

    t_factor = temperature_activity(state.temp_c, params)
    n_factor = nitrogen_activity(state.yan_mg_l)
    e_factor = ethanol_activity(state.ethanol_pct)
    s_factor = sugar_activity(state.sugar_g_l)
    biomass_factor = clamp(state.biomass_g_l / 0.85, 0.08, 1.35)

    rate = params.max_sugar_rate_g_l_h * t_factor * n_factor * e_factor * s_factor * biomass_factor
    consumed = min(state.sugar_g_l, max(0.0, rate * dt_hours))

    growth_room = clamp(1.0 - state.biomass_g_l / params.biomass_capacity_g_l)
    growth = (
        params.biomass_growth_per_h * t_factor * n_factor * e_factor
        * growth_room * dt_hours
    )
    # Ethanol stress slowly removes viable biomass late in fermentation.
    death = 0.004 * clamp((state.ethanol_pct - 12.0) / 5.0) * state.biomass_g_l * dt_hours
    biomass = max(0.02, state.biomass_g_l + growth - death)

    ethanol_gain = consumed / params.sugar_g_l_per_abv_pct
    yan_used = consumed * params.yan_consumption_mg_per_g_sugar
    co2_gain = consumed * params.co2_yield_g_per_g_sugar

    metabolic_heat = consumed * params.heat_c_per_g_l_sugar
    ambient_term = (params.ambient_temp_c - state.temp_c) * params.ambient_exchange_per_h * dt_hours
    cooling_term = 0.0
    if params.cooling_setpoint_c is not None and state.temp_c > params.cooling_setpoint_c:
        cooling_term = -(state.temp_c - params.cooling_setpoint_c) * params.cooling_strength_per_h * dt_hours
    temp = state.temp_c + metabolic_heat + ambient_term + cooling_term

    pressure_gain = co2_gain * 0.012 * clamp(params.vessel_pressure_retention)
    pressure = max(0.0, state.pressure_bar + pressure_gain)

    # VA is deliberately small in healthy fermentation and rises under hot,
    # nutrient-limited or oxygen-mismanaged conditions.
    low_n = clamp((100.0 - state.yan_mg_l) / 100.0)
    hot = clamp((state.temp_c - 29.0) / 7.0)
    oxygen_extreme = abs(clamp(params.oxygen_management_index) - 0.45) / 0.55
    va_gain = consumed * (0.00005 + 0.00016 * low_n + 0.00012 * hot + 0.00005 * oxygen_extreme)
    va = state.volatile_acidity_g_l + va_gain

    anthocyanin = state.anthocyanin_extraction
    tannin = state.tannin_extraction
    if params.maceration and params.extraction_scale > 0:
        time_factor = clamp((state.hour + dt_hours) / (24.0 * 14.0))
        temp_extract = clamp((state.temp_c - 12.0) / 18.0)
        ethanol_extract = clamp((state.ethanol_pct + ethanol_gain) / 14.0)
        anth_rate = 0.013 * params.extraction_scale * (0.65 * temp_extract + 0.35 * time_factor)
        tannin_rate = 0.0065 * params.extraction_scale * (
            0.25 * temp_extract + 0.55 * ethanol_extract + 0.20 * clamp(params.whole_cluster_fraction)
        )
        anthocyanin = clamp(anthocyanin + anth_rate * dt_hours / 24.0)
        tannin = clamp(tannin + tannin_rate * dt_hours / 24.0)

    provisional = FermentationState(
        hour=state.hour + dt_hours,
        sugar_g_l=max(0.0, state.sugar_g_l - consumed),
        ethanol_pct=state.ethanol_pct + ethanol_gain,
        yan_mg_l=max(0.0, state.yan_mg_l - yan_used),
        temp_c=temp,
        biomass_g_l=biomass,
        co2_generated_g_l=state.co2_generated_g_l + co2_gain,
        pressure_bar=pressure,
        volatile_acidity_g_l=va,
        h2s_risk=state.h2s_risk,
        stuck_risk=state.stuck_risk,
        anthocyanin_extraction=anthocyanin,
        tannin_extraction=tannin,
        finished=False,
    )
    stuck, h2s = _risk_state(provisional, params)
    finished = provisional.sugar_g_l <= 2.0
    return replace(provisional, stuck_risk=stuck, h2s_risk=h2s, finished=finished)


def run_alcoholic_fermentation(
    state: FermentationState,
    params: AlcoholicFermentationParams = AlcoholicFermentationParams(),
    *,
    max_hours: float = 720.0,
    dt_hours: float = 1.0,
) -> list[FermentationState]:
    history = [state]
    current = state
    while current.hour < max_hours and not current.finished:
        current = step_alcoholic_fermentation(current, params, dt_hours=dt_hours)
        history.append(current)
        # A severely stressed ferment can remain in the simulation rather than
        # being declared chemically impossible. Stop only when progress becomes negligible.
        if len(history) > 48:
            prior = history[-25]
            if prior.sugar_g_l - current.sugar_g_l < 0.05 and current.stuck_risk > 0.85:
                break
    return history


def malolactic_activity(state: MalolacticState, params: MalolacticParams) -> float:
    temp = exp(-((state.temp_c - params.optimum_temp_c) / 5.0) ** 2)
    ph = exp(-((state.ph - params.optimum_ph) / 0.48) ** 2)
    alcohol = clamp(1.0 - max(0.0, state.ethanol_pct - 12.0) / max(0.1, params.max_ethanol_pct - 12.0), 0.05, 1.0)
    so2 = clamp(1.0 - state.free_so2_mg_l / max(1.0, params.max_free_so2_mg_l), 0.02, 1.0)
    if state.temp_c <= params.minimum_temp_c or state.temp_c >= params.maximum_temp_c:
        temp *= 0.08
    return clamp(temp * ph * alcohol * so2)


def step_malolactic(
    state: MalolacticState,
    params: MalolacticParams = MalolacticParams(),
    *,
    dt_days: float = 1.0,
) -> MalolacticState:
    if state.finished or dt_days <= 0:
        return state
    activity = malolactic_activity(state, params)
    bacteria = clamp(state.bacterial_activity + 0.08 * activity * (1.0 - state.bacterial_activity) * dt_days)
    malic_used = min(state.malic_g_l, params.base_malic_rate_g_l_day * activity * (0.35 + bacteria) * dt_days)
    malic = max(0.0, state.malic_g_l - malic_used)
    lactic = state.lactic_g_l + malic_used * 0.90
    va = state.volatile_acidity_g_l + malic_used * 0.004 * (1.0 + clamp((state.temp_c - 23.0) / 5.0))
    completion = clamp(1.0 - malic / max(0.01, state.malic_g_l if state.day == 0 else state.malic_g_l + malic_used))
    stalled = clamp(
        0.45 * (1.0 - activity)
        + 0.30 * clamp((state.free_so2_mg_l - 20.0) / 20.0)
        + 0.25 * clamp((state.ethanol_pct - 14.0) / 3.0)
    )
    return MalolacticState(
        day=state.day + dt_days,
        malic_g_l=malic,
        lactic_g_l=lactic,
        ph=state.ph + malic_used * 0.010,
        temp_c=state.temp_c,
        ethanol_pct=state.ethanol_pct,
        free_so2_mg_l=state.free_so2_mg_l,
        bacterial_activity=bacteria,
        volatile_acidity_g_l=va,
        completion=completion,
        stalled_risk=stalled,
        finished=malic <= 0.10,
    )


def run_malolactic(
    state: MalolacticState,
    params: MalolacticParams = MalolacticParams(),
    *,
    max_days: float = 120.0,
) -> list[MalolacticState]:
    history = [state]
    current = state
    while current.day < max_days and not current.finished:
        current = step_malolactic(current, params)
        history.append(current)
        if len(history) > 15 and history[-8].malic_g_l - current.malic_g_l < 0.002 and current.stalled_risk > 0.85:
            break
    return history
