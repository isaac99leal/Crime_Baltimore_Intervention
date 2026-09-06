"""Normalized producer/importer technical observations.

This module ports the strongest trade-sheet research from the browser prototype
into the Python knowledge foundation without promoting trade copy into legal,
genetic, or historical-weather authority.

The raw JSON records remain evidence observations. They may describe a producer,
a wine, a vineyard, a vintage, viticulture, cellar process, analytical values,
bottling, or closure. They cannot by themselves establish protected-origin law,
authorized-grape law, cultivar identity/genetics, historical weather, or an
official vintage rating.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .catalog import normalize_name

DATA_DIR = Path(__file__).resolve().parent / "data" / "trade_research"


class TradeResearchError(ValueError):
    """Raised when the trade research corpus violates provenance invariants."""


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


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _stable(value: Any) -> str:
    def thaw(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {str(k): thaw(v) for k, v in item.items()}
        if isinstance(item, tuple):
            return [thaw(v) for v in item]
        return item

    return json.dumps(thaw(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class TradeFieldPolicy:
    may_establish: tuple[str, ...]
    requires_primary_or_specialist: tuple[str, ...]
    sensory_policy: str = ""

    def is_restricted_authority_claim(self, claim: str) -> bool:
        target = normalize_name(claim)
        return any(normalize_name(item) == target for item in self.requires_primary_or_specialist)


@dataclass(frozen=True)
class TradeSourceRecord:
    id: str
    name: str
    base_url: str
    source_ref: str
    roles: tuple[str, ...]
    trust_tier: str
    discovery: tuple[str, ...] = ()
    version_key_fields: tuple[str, ...] = ()
    strengths: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()


@dataclass(frozen=True)
class TradeTechnicalObservation:
    id: str
    trade_source_id: str
    source_url: str
    producer: str
    wine: str | None
    vintage: int | None
    country: str
    region: str
    vineyard: str | None
    evidence_channel: str
    source_ref: str
    fields: Mapping[str, Any]
    context: Mapping[str, Any]

    @property
    def technical_field_count(self) -> int:
        return len(self.fields)

    @property
    def entity_key(self) -> tuple[str, str, int | None]:
        return (
            normalize_name(self.producer),
            normalize_name(self.wine or ""),
            self.vintage,
        )

    def field(self, name: str, default: Any = None) -> Any:
        return self.fields.get(name, default)


@dataclass(frozen=True)
class TradeObservationConflict:
    producer: str
    wine: str | None
    vintage: int
    field: str
    observation_ids: tuple[str, ...]
    serialized_values: tuple[str, ...]


@dataclass(frozen=True)
class TradeResearchStats:
    source_count: int
    observation_count: int
    technical_field_count: int
    country_count: int
    producer_count: int
    vintage_count: int


class TradeResearchRegistry:
    """Load and query versioned trade technical observations.

    Observations are never merged by last-write-wins. Different vintages form a
    trajectory. Material disagreement for the same producer/wine/vintage/field
    remains visible as a conflict.
    """

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.field_policy = TradeFieldPolicy((), ())
        self.sources: tuple[TradeSourceRecord, ...] = ()
        self.observations: tuple[TradeTechnicalObservation, ...] = ()
        self._source_index: dict[str, TradeSourceRecord] = {}
        self._load_sources()
        self._load_observations()

    def _load_sources(self) -> None:
        source_rows: list[TradeSourceRecord] = []
        seen: set[str] = set()
        policy: TradeFieldPolicy | None = None
        files = _ordered_files("trade_source_registry")
        if not files:
            raise TradeResearchError(f"No trade source registries found in {self.data_dir}")

        for path in files:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("schemaVersion") != 1:
                raise TradeResearchError(f"Unsupported trade source schema in {path.name}")
            raw_policy = doc.get("fieldPolicy")
            if raw_policy:
                candidate = TradeFieldPolicy(
                    may_establish=tuple(raw_policy.get("tradeSheetMayEstablish", [])),
                    requires_primary_or_specialist=tuple(
                        raw_policy.get("requiresPrimaryOrSpecialistCorroboration", [])
                    ),
                    sensory_policy=str(raw_policy.get("sensoryPolicy", "")),
                )
                if policy is not None and policy != candidate:
                    raise TradeResearchError("Conflicting trade field policies")
                policy = candidate

            for row in doc.get("sources", []):
                source_id = str(row.get("id", "")).strip()
                if not source_id:
                    raise TradeResearchError(f"Missing source id in {path.name}")
                if source_id in seen:
                    raise TradeResearchError(f"Duplicate trade source id {source_id}")
                base_url = str(row.get("baseUrl", "")).strip()
                if not base_url.startswith(("https://", "http://")):
                    raise TradeResearchError(f"Trade source {source_id} lacks an absolute URL")
                record = TradeSourceRecord(
                    id=source_id,
                    name=str(row.get("name", "")).strip(),
                    base_url=base_url,
                    source_ref=str(row.get("sourceRef", "")).strip(),
                    roles=tuple(str(v) for v in row.get("role", [])),
                    trust_tier=str(row.get("trustTier", "")).strip(),
                    discovery=tuple(str(v) for v in row.get("discovery", [])),
                    version_key_fields=tuple(str(v) for v in row.get("versionKeyFields", [])),
                    strengths=tuple(str(v) for v in row.get("strengths", [])),
                    caveats=tuple(str(v) for v in row.get("caveats", [])),
                )
                if not record.name or not record.source_ref or not record.trust_tier:
                    raise TradeResearchError(f"Incomplete trade source {source_id}")
                seen.add(source_id)
                source_rows.append(record)

        self.field_policy = policy or TradeFieldPolicy((), ())
        self.sources = tuple(source_rows)
        self._source_index = {source.id: source for source in self.sources}

    def _load_observations(self) -> None:
        rows: list[TradeTechnicalObservation] = []
        seen: set[str] = set()
        files = _ordered_files("trade_tech_sheet_observations_pass")
        if not files:
            raise TradeResearchError(f"No trade observations found in {self.data_dir}")

        reserved = {
            "id", "tradeSourceId", "sourceUrl", "producer", "wine", "vintage",
            "country", "region", "vineyard", "fields", "evidenceChannel", "sourceRef",
        }
        for path in files:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("schemaVersion") != 1:
                raise TradeResearchError(f"Unsupported trade observation schema in {path.name}")
            for raw in doc.get("observations", []):
                observation_id = str(raw.get("id", "")).strip()
                if not observation_id:
                    raise TradeResearchError(f"Missing observation id in {path.name}")
                if observation_id in seen:
                    raise TradeResearchError(f"Duplicate trade observation id {observation_id}")

                source_id = str(raw.get("tradeSourceId", "")).strip()
                source = self._source_index.get(source_id)
                if source is None:
                    raise TradeResearchError(
                        f"Observation {observation_id} references unknown trade source {source_id}"
                    )
                source_url = str(raw.get("sourceUrl", "")).strip()
                if not source_url.startswith(("https://", "http://")):
                    raise TradeResearchError(f"Observation {observation_id} lacks an absolute source URL")
                source_ref = str(raw.get("sourceRef", "")).strip()
                if source_ref != source.source_ref:
                    raise TradeResearchError(
                        f"Observation {observation_id} sourceRef {source_ref!r} does not match "
                        f"registered sourceRef {source.source_ref!r}"
                    )
                producer = str(raw.get("producer", "")).strip()
                if not producer:
                    raise TradeResearchError(f"Observation {observation_id} lacks producer identity")
                fields = raw.get("fields")
                if not isinstance(fields, dict) or not fields:
                    raise TradeResearchError(f"Observation {observation_id} has no technical fields")
                vintage_raw = raw.get("vintage")
                vintage: int | None
                if vintage_raw is None:
                    vintage = None
                elif isinstance(vintage_raw, int) and 1800 <= vintage_raw <= 2200:
                    vintage = vintage_raw
                else:
                    raise TradeResearchError(
                        f"Observation {observation_id} has unsupported vintage {vintage_raw!r}"
                    )
                context = {k: v for k, v in raw.items() if k not in reserved}
                rows.append(
                    TradeTechnicalObservation(
                        id=observation_id,
                        trade_source_id=source_id,
                        source_url=source_url,
                        producer=producer,
                        wine=str(raw["wine"]).strip() if raw.get("wine") is not None else None,
                        vintage=vintage,
                        country=str(raw.get("country", "")).strip(),
                        region=str(raw.get("region", "")).strip(),
                        vineyard=str(raw["vineyard"]).strip() if raw.get("vineyard") is not None else None,
                        evidence_channel=str(raw.get("evidenceChannel", "")).strip(),
                        source_ref=source_ref,
                        fields=_freeze(fields),
                        context=_freeze(context),
                    )
                )
                if not rows[-1].country or not rows[-1].evidence_channel:
                    raise TradeResearchError(f"Observation {observation_id} lacks scope/provenance")
                seen.add(observation_id)

        self.observations = tuple(rows)

    def source(self, source_id: str) -> TradeSourceRecord | None:
        return self._source_index.get(source_id)

    def for_source(self, source_id: str) -> tuple[TradeTechnicalObservation, ...]:
        return tuple(obs for obs in self.observations if obs.trade_source_id == source_id)

    def for_producer(self, producer: str) -> tuple[TradeTechnicalObservation, ...]:
        key = normalize_name(producer)
        return tuple(obs for obs in self.observations if normalize_name(obs.producer) == key)

    def for_wine(self, producer: str, wine: str) -> tuple[TradeTechnicalObservation, ...]:
        producer_key = normalize_name(producer)
        wine_key = normalize_name(wine)
        return tuple(
            obs for obs in self.observations
            if normalize_name(obs.producer) == producer_key
            and normalize_name(obs.wine or "") == wine_key
        )

    def trajectory(self, producer: str, wine: str) -> tuple[TradeTechnicalObservation, ...]:
        rows = self.for_wine(producer, wine)
        return tuple(sorted(rows, key=lambda obs: (obs.vintage is None, obs.vintage or 0, obs.id)))

    def observations_with_field(self, field: str) -> tuple[TradeTechnicalObservation, ...]:
        return tuple(obs for obs in self.observations if field in obs.fields)

    def same_vintage_conflicts(self) -> tuple[TradeObservationConflict, ...]:
        grouped: dict[tuple[str, str, int], list[TradeTechnicalObservation]] = {}
        for obs in self.observations:
            if obs.vintage is None:
                continue
            key = (normalize_name(obs.producer), normalize_name(obs.wine or ""), obs.vintage)
            grouped.setdefault(key, []).append(obs)

        conflicts: list[TradeObservationConflict] = []
        for group in grouped.values():
            if len(group) < 2:
                continue
            fields = sorted(set().union(*(obs.fields.keys() for obs in group)))
            for field in fields:
                observations = [obs for obs in group if field in obs.fields]
                values = {_stable(obs.fields[field]) for obs in observations}
                if len(values) <= 1:
                    continue
                conflicts.append(
                    TradeObservationConflict(
                        producer=group[0].producer,
                        wine=group[0].wine,
                        vintage=group[0].vintage or 0,
                        field=field,
                        observation_ids=tuple(obs.id for obs in observations),
                        serialized_values=tuple(sorted(values)),
                    )
                )
        return tuple(sorted(conflicts, key=lambda c: (c.producer, c.wine or "", c.vintage, c.field)))

    def stats(self) -> TradeResearchStats:
        vintages = {obs.vintage for obs in self.observations if obs.vintage is not None}
        return TradeResearchStats(
            source_count=len(self.sources),
            observation_count=len(self.observations),
            technical_field_count=sum(obs.technical_field_count for obs in self.observations),
            country_count=len({obs.country for obs in self.observations}),
            producer_count=len({normalize_name(obs.producer) for obs in self.observations}),
            vintage_count=len(vintages),
        )

    def authority_restrictions(self) -> tuple[str, ...]:
        return self.field_policy.requires_primary_or_specialist

    def assert_trade_can_support(self, claim_kind: str) -> None:
        if self.field_policy.is_restricted_authority_claim(claim_kind):
            raise TradeResearchError(
                f"Trade evidence cannot independently establish {claim_kind!r}; "
                "use primary regulator/genetic/weather authority."
            )


def load_trade_research() -> TradeResearchRegistry:
    return TradeResearchRegistry()
