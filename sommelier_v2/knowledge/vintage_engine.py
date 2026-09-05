"""Daily-weather vintage mechanics for Sommelier Simulator v2.

The engine converts a weather series into viticultural state and wine-style
modifiers. It does not invent historical weather. Historical simulations must be
fed observed or explicitly generated weather records with provenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import exp


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class DailyWeather:
    day_of_year: int
    tmin_c: float
    tmax_c: float
    rain_mm: float = 0.0
    humidity_pct: float = 65.0
    solar_mj_m2: float = 18.0
    wind_m_s: float = 2.0
    hail: bool = False

    @property
    def mean_temp_c(self) -> float:
        return (self.tmin_c + self.tmax_c) / 2.0


@dataclass(frozen=True)
class VintageModelParams:
    base_temp_c: float = 10.0
    budbreak_gdd: float = 80.0
    flowering_gdd: float = 360.0
    veraison_gdd: float = 900.0
    target_harvest_gdd: float = 1350.0
    max_harvest_gdd: float = 1650.0
    frost_damage_temp_c: float = -1.0
    heatwave_temp_c: float = 35.0
    extreme_heat_temp_c: float = 40.0
    hot_night_temp_c: float = 20.0
    field_capacity_mm: float = 140.0
    initial_soil_water_mm: float = 100.0
    drought_stress_threshold_mm: float = 35.0
    harvest_rain_window_days: int = 28
    flowering_window_days: int = 18
    variety_acidity_retention: float = 0.5
    variety_drought_tolerance: float = 0.5
    variety_heat_sensitivity: float = 0.5
    variety_botrytis_susceptibility: float = 0.5
    variety_rot_susceptibility: float = 0.5


@dataclass
class VintageDayState:
    day_of_year: int
    cumulative_gdd: float
    soil_water_mm: float
    water_stress: float
    disease_pressure: float
    botrytis_pressure: float
    canopy_health: float
    berry_growth_index: float
    sugar_ripeness: float
    phenolic_ripeness: float
    acidity_retention: float
    yield_index: float
    frost_damage: float
    hail_damage: float


@dataclass(frozen=True)
class VintageOutcome:
    budbreak_day: int | None
    flowering_day: int | None
    veraison_day: int | None
    harvest_day: int | None
    growing_degree_days: float
    growing_season_rain_mm: float
    harvest_window_rain_mm: float
    frost_events: int
    hail_events: int
    heatwave_days: int
    extreme_heat_days: int
    hot_nights: int
    disease_pressure: float
    botrytis_pressure: float
    drought_stress: float
    yield_index: float
    ripeness_index: float
    phenolic_ripeness_index: float
    acidity_retention_index: float
    tannin_quality_index: float
    concentration_index: float
    heterogeneity_index: float
    early_accessibility: float
    longevity_modifier: float
    style_tags: tuple[str, ...] = ()
    daily_states: tuple[VintageDayState, ...] = field(default_factory=tuple, repr=False)


def _evapotranspiration_proxy(weather: DailyWeather) -> float:
    # A bounded radiation/temperature/wind proxy, adequate for game mechanics.
    temp_term = max(0.0, weather.mean_temp_c - 5.0) * 0.12
    solar_term = max(0.0, weather.solar_mj_m2) * 0.055
    wind_term = max(0.0, weather.wind_m_s) * 0.12
    humidity_term = clamp((100.0 - weather.humidity_pct) / 100.0) * 1.2
    return max(0.3, temp_term + solar_term + wind_term + humidity_term)


def _stage_day(cumulative: float, threshold: float, weather: DailyWeather, current: int | None) -> int | None:
    return weather.day_of_year if current is None and cumulative >= threshold else current


def simulate_vintage(
    weather_days: list[DailyWeather],
    params: VintageModelParams = VintageModelParams(),
) -> VintageOutcome:
    if not weather_days:
        raise ValueError("weather_days must not be empty")
    days = sorted(weather_days, key=lambda d: d.day_of_year)

    gdd = 0.0
    soil = clamp(params.initial_soil_water_mm, 0.0, params.field_capacity_mm)
    budbreak_day = flowering_day = veraison_day = harvest_day = None
    growing_rain = 0.0
    frost_events = hail_events = heatwave_days = extreme_heat_days = hot_nights = 0
    frost_damage = hail_damage = 0.0
    disease = botrytis = drought_peak = 0.0
    canopy_health = 1.0
    yield_index = 1.0
    sugar = phenolics = 0.0
    acid = clamp(0.55 + 0.45 * params.variety_acidity_retention)
    states: list[VintageDayState] = []
    harvest_index = len(days) - 1

    for i, weather in enumerate(days):
        mean = weather.mean_temp_c
        daily_gdd = max(0.0, mean - params.base_temp_c)
        gdd += daily_gdd
        budbreak_day = _stage_day(gdd, params.budbreak_gdd, weather, budbreak_day)
        flowering_day = _stage_day(gdd, params.flowering_gdd, weather, flowering_day)
        veraison_day = _stage_day(gdd, params.veraison_gdd, weather, veraison_day)

        active = budbreak_day is not None
        if active:
            growing_rain += max(0.0, weather.rain_mm)

        soil = min(params.field_capacity_mm, soil + max(0.0, weather.rain_mm))
        et = _evapotranspiration_proxy(weather)
        soil = max(0.0, soil - et)
        water_stress = clamp(
            (params.drought_stress_threshold_mm - soil) / max(1.0, params.drought_stress_threshold_mm)
        )
        water_stress *= (1.0 - 0.55 * params.variety_drought_tolerance)
        drought_peak = max(drought_peak, water_stress)

        if active and weather.tmin_c <= params.frost_damage_temp_c and (veraison_day is None):
            frost_events += 1
            severity = clamp((params.frost_damage_temp_c - weather.tmin_c + 0.5) / 5.0)
            frost_damage = clamp(frost_damage + severity * 0.28)
            yield_index *= max(0.35, 1.0 - severity * 0.24)

        if active and weather.hail:
            hail_events += 1
            stage_factor = 1.0 if veraison_day is not None else 0.75
            hit = 0.16 * stage_factor
            hail_damage = clamp(hail_damage + hit)
            yield_index *= 1.0 - hit

        if active and weather.tmax_c >= params.heatwave_temp_c:
            heatwave_days += 1
        if active and weather.tmax_c >= params.extreme_heat_temp_c:
            extreme_heat_days += 1
            canopy_health *= 1.0 - 0.015 * (0.5 + params.variety_heat_sensitivity)
        if active and weather.tmin_c >= params.hot_night_temp_c:
            hot_nights += 1

        wet_leaf = clamp(weather.rain_mm / 10.0) * clamp(weather.humidity_pct / 85.0)
        temp_disease = exp(-((mean - 22.0) / 8.0) ** 2)
        daily_disease = wet_leaf * temp_disease
        disease = clamp(disease * 0.96 + daily_disease * 0.08)
        canopy_health *= 1.0 - 0.0025 * disease

        if veraison_day is not None:
            botrytis_day = (
                clamp(weather.rain_mm / 12.0)
                * clamp((weather.humidity_pct - 70.0) / 25.0)
                * exp(-((mean - 19.0) / 7.0) ** 2)
                * (0.45 + 0.75 * params.variety_botrytis_susceptibility)
            )
            botrytis = clamp(botrytis * 0.94 + botrytis_day * 0.10)

        # Flowering rain and cold reduce fruit set.
        if flowering_day is not None and abs(weather.day_of_year - flowering_day) <= params.flowering_window_days // 2:
            flowering_penalty = clamp(weather.rain_mm / 20.0) * 0.018
            if mean < 15.0:
                flowering_penalty += clamp((15.0 - mean) / 8.0) * 0.018
            yield_index *= max(0.94, 1.0 - flowering_penalty)

        if veraison_day is not None:
            ripening_heat = clamp((mean - 12.0) / 16.0)
            water_optimum = 1.0 - abs(clamp(water_stress) - 0.25) * 0.75
            sugar += 0.0080 * ripening_heat * max(0.25, water_optimum) * canopy_health
            solar = clamp(weather.solar_mj_m2 / 24.0)
            phenolics += 0.0065 * solar * ripening_heat * (0.65 + 0.35 * water_optimum)
            # Hot nights and very high maxima accelerate respiratory acid loss.
            acid_loss = 0.0012 * ripening_heat
            if weather.tmin_c >= params.hot_night_temp_c:
                acid_loss += 0.0032 * (0.5 + 0.5 * (1.0 - params.variety_acidity_retention))
            if weather.tmax_c >= params.heatwave_temp_c:
                acid_loss += 0.0025 * (0.5 + params.variety_heat_sensitivity)
            acid = clamp(acid - acid_loss)

        berry_growth = clamp(0.45 + 0.35 * (soil / max(1.0, params.field_capacity_mm)) - 0.20 * water_stress)
        sugar_ripeness = clamp(max(sugar, (gdd - params.veraison_gdd) / max(1.0, params.target_harvest_gdd - params.veraison_gdd)))
        phenolic_ripeness = clamp(phenolics)

        # Harvest when thermal target and practical ripeness are reached. Severe
        # late rot/rain can force an earlier pick after veraison.
        forced_by_rot = veraison_day is not None and botrytis > 0.72 and sugar_ripeness > 0.72
        reached_target = gdd >= params.target_harvest_gdd and sugar_ripeness >= 0.88
        overripe_limit = gdd >= params.max_harvest_gdd
        if harvest_day is None and (reached_target or forced_by_rot or overripe_limit):
            harvest_day = weather.day_of_year
            harvest_index = i

        states.append(VintageDayState(
            day_of_year=weather.day_of_year,
            cumulative_gdd=gdd,
            soil_water_mm=soil,
            water_stress=water_stress,
            disease_pressure=disease,
            botrytis_pressure=botrytis,
            canopy_health=clamp(canopy_health),
            berry_growth_index=berry_growth,
            sugar_ripeness=sugar_ripeness,
            phenolic_ripeness=phenolic_ripeness,
            acidity_retention=acid,
            yield_index=clamp(yield_index, 0.0, 1.4),
            frost_damage=frost_damage,
            hail_damage=hail_damage,
        ))
        if harvest_day is not None:
            break

    if harvest_day is None:
        harvest_day = days[harvest_index].day_of_year

    harvest_weather = days[:harvest_index + 1]
    window_start = harvest_day - params.harvest_rain_window_days
    harvest_rain = sum(d.rain_mm for d in harvest_weather if d.day_of_year >= window_start)
    late_rain_penalty = clamp(harvest_rain / 120.0)
    rot_penalty = clamp(botrytis * (0.5 + params.variety_rot_susceptibility * 0.6))

    final = states[-1]
    ripeness = clamp(final.sugar_ripeness * (1.0 - 0.15 * late_rain_penalty))
    phenolic = clamp(final.phenolic_ripeness * (1.0 - 0.12 * disease))
    concentration = clamp(
        0.52
        + 0.24 * clamp(drought_peak / 0.7)
        + 0.20 * ripeness
        - 0.24 * late_rain_penalty
        - 0.16 * rot_penalty
    )
    tannin_quality = clamp(0.20 + 0.55 * phenolic + 0.15 * final.acidity_retention - 0.20 * extreme_heat_days / 12.0)
    heterogeneity = clamp(
        0.10 + 0.45 * frost_damage + 0.45 * hail_damage + 0.25 * disease + 0.20 * drought_peak
    )
    yield_final = clamp(yield_index * (1.0 - 0.18 * rot_penalty), 0.0, 1.4)
    early_accessibility = clamp(0.65 + 0.20 * ripeness - 0.25 * tannin_quality + 0.10 * late_rain_penalty)
    longevity = clamp(
        0.55 + 0.30 * tannin_quality + 0.30 * final.acidity_retention
        + 0.20 * concentration - 0.28 * rot_penalty - 0.18 * heterogeneity,
        0.25, 1.45,
    )

    tags: list[str] = []
    if frost_events:
        tags.append("spring_frost")
    if hail_events:
        tags.append("hail_affected")
    if heatwave_days >= 7:
        tags.append("heatwave_vintage")
    if drought_peak >= 0.65:
        tags.append("drought_stress")
    if harvest_rain >= 70:
        tags.append("wet_harvest")
    if botrytis >= 0.55:
        tags.append("botrytis_pressure")
    if final.acidity_retention >= 0.70:
        tags.append("high_acid_retention")
    if ripeness >= 0.90 and concentration >= 0.70:
        tags.append("ripe_concentrated")
    if heterogeneity >= 0.55:
        tags.append("heterogeneous")

    return VintageOutcome(
        budbreak_day=budbreak_day,
        flowering_day=flowering_day,
        veraison_day=veraison_day,
        harvest_day=harvest_day,
        growing_degree_days=gdd,
        growing_season_rain_mm=growing_rain,
        harvest_window_rain_mm=harvest_rain,
        frost_events=frost_events,
        hail_events=hail_events,
        heatwave_days=heatwave_days,
        extreme_heat_days=extreme_heat_days,
        hot_nights=hot_nights,
        disease_pressure=disease,
        botrytis_pressure=botrytis,
        drought_stress=drought_peak,
        yield_index=yield_final,
        ripeness_index=ripeness,
        phenolic_ripeness_index=phenolic,
        acidity_retention_index=final.acidity_retention,
        tannin_quality_index=tannin_quality,
        concentration_index=concentration,
        heterogeneity_index=heterogeneity,
        early_accessibility=early_accessibility,
        longevity_modifier=longevity,
        style_tags=tuple(tags),
        daily_states=tuple(states),
    )
