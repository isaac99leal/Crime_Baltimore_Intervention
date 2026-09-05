"""Continuous bottle-aging model.

This module intentionally produces simulation state, not historical fact. Curves are
selected from explicit archetypes and can later be modified by vintage, winemaking,
storage, closure, bottle size, and chemistry.
"""
from __future__ import annotations

import math
from dataclasses import replace

from .schema import AgingArchetype, AgingState


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _exp_half_life(age: float, half_life: float) -> float:
    if half_life <= 0:
        return 0.0
    return 2.0 ** (-max(0.0, age) / half_life)


def _logistic(age: float, midpoint: float, slope: float = 1.0) -> float:
    slope = max(0.05, slope)
    x = (age - midpoint) / slope
    if x > 60:
        return 1.0
    if x < -60:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _gaussian(age: float, center: float, width: float) -> float:
    width = max(0.25, width)
    return math.exp(-0.5 * ((age - center) / width) ** 2)


def state_at_age(
    archetype: AgingArchetype,
    age_years: float,
    *,
    longevity_modifier: float = 1.0,
    storage_modifier: float = 1.0,
    oxygen_modifier: float = 1.0,
    bottle_size_modifier: float = 1.0,
) -> AgingState:
    """Return a continuous aging state at a given bottle age.

    ``longevity_modifier`` > 1 stretches development. Poor storage and higher
    oxygen exposure accelerate it. Larger bottles can use a modifier > 1.
    """
    age_years = max(0.0, age_years)
    stretch = max(
        0.2,
        longevity_modifier * bottle_size_modifier /
        max(0.2, storage_modifier * oxygen_modifier),
    )
    age = age_years / stretch

    primary = _exp_half_life(age, archetype.primary_half_life_years)
    floral = _exp_half_life(age, archetype.floral_half_life_years)
    tertiary_rise = _logistic(
        age,
        archetype.tertiary_onset_years,
        max(0.4, archetype.tertiary_onset_years * 0.18),
    )
    tertiary_fall = _exp_half_life(
        max(0.0, age - archetype.tertiary_peak_years),
        max(1.0, archetype.decline_half_life_years * 1.3),
    )
    tertiary = tertiary_rise * tertiary_fall

    tannin = _exp_half_life(age, archetype.tannin_softening_half_life_years)
    freshness = _exp_half_life(age, archetype.freshness_half_life_years)

    oxidation = _clamp01(
        _logistic(
            age,
            archetype.oxidation_onset_years,
            max(0.5, 1.0 / max(0.05, archetype.oxidation_rate)),
        )
    )
    complexity = _gaussian(
        age,
        archetype.complexity_peak_years,
        max(1.0, archetype.peak_years / 1.7),
    )
    sediment = _logistic(
        age,
        archetype.sediment_onset_years,
        max(0.5, archetype.sediment_onset_years * 0.2),
    )
    color_evolution = _clamp01(1.0 - math.exp(-archetype.color_shift_rate * age))

    maturity = _logistic(
        age,
        archetype.maturity_years,
        max(0.5, archetype.maturity_years * 0.2),
    )
    decline = _exp_half_life(
        max(0.0, age - (archetype.maturity_years + archetype.peak_years)),
        archetype.decline_half_life_years,
    )
    condition = _clamp01((0.25 + 0.75 * maturity) * decline)

    return AgingState(
        age_years=age_years,
        primary_fruit=_clamp01(primary),
        floral=_clamp01(floral),
        tertiary=_clamp01(tertiary),
        tannin_structure=_clamp01(tannin),
        freshness=_clamp01(freshness),
        oxidation=oxidation,
        complexity=_clamp01(complexity),
        sediment=_clamp01(sediment),
        color_evolution=color_evolution,
        condition=condition,
    )


def modified_archetype(
    archetype: AgingArchetype,
    *,
    acid_factor: float = 1.0,
    tannin_factor: float = 1.0,
    sugar_factor: float = 1.0,
    fortified_factor: float = 1.0,
) -> AgingArchetype:
    """Stretch an archetype using structural preservation factors.

    This is a simulation prior. It does not assert a scientific causal coefficient.
    """
    factor = max(
        0.35,
        0.35 * acid_factor
        + 0.30 * tannin_factor
        + 0.20 * sugar_factor
        + 0.15 * fortified_factor,
    )
    return replace(
        archetype,
        maturity_years=archetype.maturity_years * factor,
        peak_years=archetype.peak_years * factor,
        decline_half_life_years=archetype.decline_half_life_years * factor,
        primary_half_life_years=archetype.primary_half_life_years * factor,
        floral_half_life_years=archetype.floral_half_life_years * factor,
        tertiary_onset_years=archetype.tertiary_onset_years * factor,
        tertiary_peak_years=archetype.tertiary_peak_years * factor,
        tannin_softening_half_life_years=archetype.tannin_softening_half_life_years * factor,
        freshness_half_life_years=archetype.freshness_half_life_years * factor,
        oxidation_onset_years=archetype.oxidation_onset_years * factor,
        complexity_peak_years=archetype.complexity_peak_years * factor,
        sediment_onset_years=archetype.sediment_onset_years * factor,
    )
