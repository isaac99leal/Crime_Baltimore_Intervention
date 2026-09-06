"""Sourced historical-vintage evidence and bounded simulation signals.

This module deliberately does not manufacture daily weather. A regional harvest
report, regulator vintage note, or authority year ledger can establish exact
year facts and can carry an explicitly derived bounded simulation signal. It
cannot be converted into a synthetic meteorological time series without a
separate weather-generation model that labels its output as synthetic.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .catalog import normalize_name

DATA_DIR = Path(__file__).resolve().parent / "data" / "vintage_research"


class HistoricalVintageError(ValueError):
    """Raised when historical-vintage provenance or schema invariants fail."""


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _ordered_files(prefix: str) -> list[Path]:
    def key(path: Path) -> tuple[int, str]:
        stem = path.stem
        if "_pass" not in stem:
            return (0, stem)
        try:
            return (int(stem.rsplit("_pass", 1)[1]), stem)
        except ValueError:
            return (9999, stem)

    return sorted(DATA_DIR.glob(f"{prefix}*.json"), key=key)


@dataclass(frozen=True)
class HistoricalVintageSignal:
    """Explicitly derived, bounded non-authoritative simulation modifiers."""

    confidence: int
    acidity: float
    ripeness: float
    concentration: float
    tannin_ripeness: float
    aromatic_freshness: float
    disease_pressure: float
    yield_modifier: float
    ageability: float
    botrytis_suitability: float

    def as_dict(self) -> Mapping[str, float]:
        return MappingProxyType(
            {
                "acidity": self.acidity,
                "ripeness": self.ripeness,
                "concentration": self.concentration,
                "tannin_ripeness": self.tannin_ripeness,
                "aromatic_freshness": self.aromatic_freshness,
                "disease_pressure": self.disease_pressure,
                "yield": self.yield_modifier,
                "ageability": self.ageability,
                "botrytis_suitability": self.botrytis_suitability,
            }
        )


@dataclass(frozen=True)
class HistoricalVintageObservation:
    id: str
    environment_profile_id: str | None
    country: str
    region: str
    year: int
    growing_season: Mapping[str, Any]
    style_effects: tuple[str, ...]
    published_drink_window_years: tuple[int, int] | None
    signal: HistoricalVintageSignal
    source_refs: tuple[str, ...]

    @property
    def key(self) -> tuple[str, str, int]:
        return (normalize_name(self.country), normalize_name(self.region), self.year)

    def require_daily_weather(self) -> None:
        """Fail explicitly instead of silently converting prose into weather."""
        raise HistoricalVintageError(
            f"{self.id} contains sourced season evidence, not a daily weather series. "
            "Use observed daily weather or a separately labelled synthetic-weather model."
        )


@dataclass(frozen=True)
class AuthorityVintageRating:
    region: str
    year: int
    rating: str
    source_refs: tuple[str, ...]


@dataclass(frozen=True)
class HistoricalVintageArchive:
    id: str
    country: str
    modern_geographic_reference: str
    product_family: str
    record_status: str
    earliest_year: int
    latest_year: int
    years: tuple[int, ...]
    historical_identity_note: str
    declaration_note: str
    source_refs: tuple[str, ...]

    def explicitly_lists(self, year: int) -> bool:
        """Return only explicit year inclusion, never inferred range coverage."""
        return year in self.years


@dataclass(frozen=True)
class HistoricalVintageStats:
    observation_count: int
    authority_rating_count: int
    archive_count: int
    country_count: int
    region_count: int
    earliest_observation_year: int
    latest_observation_year: int


class HistoricalVintageRegistry:
    """Versioned source-first registry for exact-year vintage evidence."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.observations: tuple[HistoricalVintageObservation, ...] = ()
        self.authority_ratings: tuple[AuthorityVintageRating, ...] = ()
        self.archives: tuple[HistoricalVintageArchive, ...] = ()
        self._observation_index: dict[tuple[str, str, int], HistoricalVintageObservation] = {}
        self._load_observations()
        self._load_archives()

    @staticmethod
    def _signal(raw: Mapping[str, Any], observation_id: str) -> HistoricalVintageSignal:
        if raw.get("derived") is not True:
            raise HistoricalVintageError(
                f"{observation_id} matrix modifiers must be explicitly marked derived"
            )
        confidence = raw.get("confidence")
        if not isinstance(confidence, int) or not 1 <= confidence <= 5:
            raise HistoricalVintageError(
                f"{observation_id} has invalid derived-signal confidence {confidence!r}"
            )
        names = {
            "acidity": "acidity",
            "ripeness": "ripeness",
            "concentration": "concentration",
            "tanninRipeness": "tannin_ripeness",
            "aromaticFreshness": "aromatic_freshness",
            "diseasePressure": "disease_pressure",
            "yield": "yield_modifier",
            "ageability": "ageability",
            "botrytisSuitability": "botrytis_suitability",
        }
        values: dict[str, float] = {}
        for source_name, target_name in names.items():
            value = raw.get(source_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise HistoricalVintageError(
                    f"{observation_id} is missing numeric derived modifier {source_name}"
                )
            numeric = float(value)
            if not -1.0 <= numeric <= 1.0:
                raise HistoricalVintageError(
                    f"{observation_id} modifier {source_name} must be bounded -1..+1"
                )
            values[target_name] = numeric
        return HistoricalVintageSignal(confidence=confidence, **values)

    def _load_observations(self) -> None:
        rows: list[HistoricalVintageObservation] = []
        ratings: list[AuthorityVintageRating] = []
        seen_ids: set[str] = set()
        rating_keys: set[tuple[str, int, str]] = set()
        files = _ordered_files("vintage_observations")
        if not files:
            raise HistoricalVintageError(f"No historical vintage observations found in {self.data_dir}")

        for path in files:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("schemaVersion") != 1:
                raise HistoricalVintageError(f"Unsupported vintage schema in {path.name}")
            for raw in doc.get("observations", []):
                observation_id = str(raw.get("id", "")).strip()
                if not observation_id or observation_id in seen_ids:
                    raise HistoricalVintageError(
                        f"Missing or duplicate vintage observation id {observation_id!r}"
                    )
                country = str(raw.get("country", "")).strip()
                region = str(raw.get("region", "")).strip()
                year = raw.get("year")
                sources = tuple(str(v) for v in raw.get("sourceRefs", []))
                if not country or not region or not isinstance(year, int) or not sources:
                    raise HistoricalVintageError(f"Incomplete scope/provenance for {observation_id}")
                season = raw.get("growingSeason")
                if not isinstance(season, dict) or not season:
                    raise HistoricalVintageError(f"{observation_id} has no growing-season evidence")
                window_raw = raw.get("publishedDrinkWindowYears")
                window = None
                if window_raw is not None:
                    if (
                        not isinstance(window_raw, list)
                        or len(window_raw) != 2
                        or not all(isinstance(v, int) for v in window_raw)
                    ):
                        raise HistoricalVintageError(
                            f"{observation_id} has invalid published drink window"
                        )
                    window = (window_raw[0], window_raw[1])

                observation = HistoricalVintageObservation(
                    id=observation_id,
                    environment_profile_id=(
                        str(raw["environmentProfileId"])
                        if raw.get("environmentProfileId") is not None
                        else None
                    ),
                    country=country,
                    region=region,
                    year=year,
                    growing_season=_freeze(season),
                    style_effects=tuple(str(v) for v in raw.get("styleEffects", [])),
                    published_drink_window_years=window,
                    signal=self._signal(raw.get("matrixModifiers", {}), observation_id),
                    source_refs=sources,
                )
                if observation.key in self._observation_index:
                    raise HistoricalVintageError(
                        f"Duplicate country/region/year vintage observation {observation.key}"
                    )
                seen_ids.add(observation_id)
                rows.append(observation)
                self._observation_index[observation.key] = observation

            for raw in doc.get("authorityRatings", []):
                region = str(raw.get("region", "")).strip()
                rating = str(raw.get("rating", "")).strip()
                year = raw.get("year")
                sources = tuple(str(v) for v in raw.get("sourceRefs", []))
                if not region or not rating or not isinstance(year, int) or not sources:
                    raise HistoricalVintageError(f"Incomplete authority rating in {path.name}")
                key = (normalize_name(region), year, normalize_name(rating))
                if key in rating_keys:
                    raise HistoricalVintageError(f"Duplicate authority vintage rating {key}")
                rating_keys.add(key)
                ratings.append(
                    AuthorityVintageRating(
                        region=region,
                        year=year,
                        rating=rating,
                        source_refs=sources,
                    )
                )

        self.observations = tuple(rows)
        self.authority_ratings = tuple(ratings)

    def _load_archives(self) -> None:
        archives: list[HistoricalVintageArchive] = []
        seen: set[str] = set()
        files = _ordered_files("historical_vintage_archives")
        if not files:
            raise HistoricalVintageError(f"No historical vintage archives found in {self.data_dir}")

        for path in files:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("schemaVersion") != 1:
                raise HistoricalVintageError(f"Unsupported vintage archive schema in {path.name}")
            for raw in doc.get("archives", []):
                archive_id = str(raw.get("id", "")).strip()
                if not archive_id or archive_id in seen:
                    raise HistoricalVintageError(f"Missing or duplicate vintage archive id {archive_id!r}")
                earliest = raw.get("earliestYear")
                latest = raw.get("latestYear")
                years_raw = raw.get("years", [])
                sources = tuple(str(v) for v in raw.get("sourceRefs", []))
                if (
                    not isinstance(earliest, int)
                    or not isinstance(latest, int)
                    or earliest > latest
                    or not isinstance(years_raw, list)
                    or not all(isinstance(v, int) for v in years_raw)
                    or not sources
                ):
                    raise HistoricalVintageError(f"Invalid coverage for vintage archive {archive_id}")
                years = tuple(years_raw)
                if len(set(years)) != len(years):
                    raise HistoricalVintageError(f"Duplicate year inside vintage archive {archive_id}")
                if any(year < earliest or year > latest for year in years):
                    raise HistoricalVintageError(f"Out-of-range year inside vintage archive {archive_id}")
                archives.append(
                    HistoricalVintageArchive(
                        id=archive_id,
                        country=str(raw.get("country", "")).strip(),
                        modern_geographic_reference=str(raw.get("modernGeographicReference", "")).strip(),
                        product_family=str(raw.get("productFamily", "")).strip(),
                        record_status=str(raw.get("recordStatus", "")).strip(),
                        earliest_year=earliest,
                        latest_year=latest,
                        years=years,
                        historical_identity_note=str(raw.get("historicalIdentityNote", "")).strip(),
                        declaration_note=str(raw.get("declarationNote", "")).strip(),
                        source_refs=sources,
                    )
                )
                if not archives[-1].country or not archives[-1].modern_geographic_reference:
                    raise HistoricalVintageError(f"Incomplete archive identity for {archive_id}")
                seen.add(archive_id)

        self.archives = tuple(archives)

    def observation(self, country: str, region: str, year: int) -> HistoricalVintageObservation | None:
        return self._observation_index.get((normalize_name(country), normalize_name(region), year))

    def region_history(self, country: str, region: str) -> tuple[HistoricalVintageObservation, ...]:
        country_key = normalize_name(country)
        region_key = normalize_name(region)
        rows = [
            obs for obs in self.observations
            if normalize_name(obs.country) == country_key and normalize_name(obs.region) == region_key
        ]
        return tuple(sorted(rows, key=lambda obs: obs.year))

    def authority_rating(self, region: str, year: int) -> tuple[AuthorityVintageRating, ...]:
        key = normalize_name(region)
        return tuple(
            rating for rating in self.authority_ratings
            if normalize_name(rating.region) == key and rating.year == year
        )

    def archive(self, archive_id: str) -> HistoricalVintageArchive | None:
        return next((archive for archive in self.archives if archive.id == archive_id), None)

    def stats(self) -> HistoricalVintageStats:
        years = [obs.year for obs in self.observations]
        return HistoricalVintageStats(
            observation_count=len(self.observations),
            authority_rating_count=len(self.authority_ratings),
            archive_count=len(self.archives),
            country_count=len({obs.country for obs in self.observations}),
            region_count=len({(obs.country, obs.region) for obs in self.observations}),
            earliest_observation_year=min(years),
            latest_observation_year=max(years),
        )


def load_historical_vintages() -> HistoricalVintageRegistry:
    return HistoricalVintageRegistry()
