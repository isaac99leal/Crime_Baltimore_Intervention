"""Evidence-facing climate indices derived from daily vineyard weather.

These indices complement, rather than replace, ``vintage_engine``. They expose
transparent climate descriptors that can be stored with a vintage and compared
across sites. Historical values must come from observed weather or a separately
identified synthetic weather generator.

The calculations intentionally operate on the supplied interval. They do not
assume a hemisphere or silently substitute a calendar growing season.
"""
from __future__ import annotations

from dataclasses import dataclass

from .vintage_engine import DailyWeather


@dataclass(frozen=True)
class VintageClimateIndices:
    interval_start_day: int
    interval_end_day: int
    sample_days: int
    base_temp_c: float
    growing_degree_days_c: float
    huglin_heat_sum: float
    growing_season_mean_temp_c: float
    mean_diurnal_range_c: float
    growing_season_rain_mm: float
    preharvest_rain_30d_mm: float
    preharvest_mean_min_temp_30d_c: float
    hot_days_35c: int
    extreme_heat_days_40c: int
    hot_nights_20c: int
    frost_days_minus1c: int
    rain_days_1mm: int
    evidence: tuple[str, ...] = (
        "UC ANR: Winkler/GDD uses a 10 C base and a defined growing-season interval.",
        "Viticulture literature commonly uses GDD/Winkler, Huglin heat, growing-season temperature, cool-night and rainfall indices.",
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def calculate_vintage_climate_indices(
    weather_days: list[DailyWeather],
    *,
    base_temp_c: float = 10.0,
    day_length_coefficient: float = 1.0,
    interval_start_day: int | None = None,
    interval_end_day: int | None = None,
    harvest_day: int | None = None,
) -> VintageClimateIndices:
    """Calculate transparent thermal, rain, and night-temperature descriptors.

    ``huglin_heat_sum`` is the Huglin thermal expression over the supplied
    interval: sum((((Tmean-base) + (Tmax-base)) / 2) * k), with negative daily
    contributions clipped to zero. A caller that wants the conventional Huglin
    Index must supply the jurisdiction-appropriate seasonal interval and
    latitude/day-length coefficient.

    ``preharvest_mean_min_temp_30d_c`` is deliberately not named the formal Cool
    Night Index because this engine has day-of-year values rather than a calendar
    month and hemisphere. It is a harvest-relative analogue that works for both
    hemispheres.
    """
    if not weather_days:
        raise ValueError("weather_days must not be empty")
    if base_temp_c < -20.0 or base_temp_c > 30.0:
        raise ValueError("base_temp_c is outside the supported range")
    if day_length_coefficient <= 0.0 or day_length_coefficient > 2.0:
        raise ValueError("day_length_coefficient must be >0 and <=2")

    ordered = sorted(weather_days, key=lambda day: day.day_of_year)
    start = interval_start_day if interval_start_day is not None else ordered[0].day_of_year
    end = interval_end_day if interval_end_day is not None else ordered[-1].day_of_year
    if end < start:
        raise ValueError("interval_end_day must be >= interval_start_day")

    days = [day for day in ordered if start <= day.day_of_year <= end]
    if not days:
        raise ValueError("no weather observations fall inside the requested interval")

    harvest = harvest_day if harvest_day is not None else days[-1].day_of_year
    if harvest < start or harvest > end:
        raise ValueError("harvest_day must fall inside the requested interval")

    means = [day.mean_temp_c for day in days]
    gdd = sum(max(0.0, mean - base_temp_c) for mean in means)
    huglin = sum(
        max(
            0.0,
            (((day.mean_temp_c - base_temp_c) + (day.tmax_c - base_temp_c)) / 2.0)
            * day_length_coefficient,
        )
        for day in days
    )
    preharvest = [
        day for day in days
        if harvest - 29 <= day.day_of_year <= harvest
    ]

    return VintageClimateIndices(
        interval_start_day=start,
        interval_end_day=end,
        sample_days=len(days),
        base_temp_c=base_temp_c,
        growing_degree_days_c=gdd,
        huglin_heat_sum=huglin,
        growing_season_mean_temp_c=_mean(means),
        mean_diurnal_range_c=_mean([day.tmax_c - day.tmin_c for day in days]),
        growing_season_rain_mm=sum(max(0.0, day.rain_mm) for day in days),
        preharvest_rain_30d_mm=sum(max(0.0, day.rain_mm) for day in preharvest),
        preharvest_mean_min_temp_30d_c=_mean([day.tmin_c for day in preharvest]),
        hot_days_35c=sum(day.tmax_c >= 35.0 for day in days),
        extreme_heat_days_40c=sum(day.tmax_c >= 40.0 for day in days),
        hot_nights_20c=sum(day.tmin_c >= 20.0 for day in days),
        frost_days_minus1c=sum(day.tmin_c <= -1.0 for day in days),
        rain_days_1mm=sum(day.rain_mm >= 1.0 for day in days),
    )
