"""Producer/grower vineyard and micro-site observations.

This registry is deliberately separate from the legal/institutional named-site
registry. A producer map can establish a source-stated block, clone, rootstock,
planting year, parcel size, slope, aspect, soil, or similar viticultural fact.
It cannot independently establish an AVA boundary, protected-origin law, grape
legality, or a universal sensory/terroir rule.

Conflicting source-context observations remain separate records. The registry
never resolves them by last-write-wins.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .catalog import normalize_name

DATA_DIR = Path(__file__).resolve().parent / "data" / "site_research"


class SiteResearchError(ValueError):
    """Raised when micro-site evidence violates provenance invariants."""


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
class SiteResearchSource:
    id: str
    publisher: str
    title: str
    url: str
    jurisdiction: str
    kind: str
    accessed: str


@dataclass(frozen=True)
class SiteDataQualityFlag:
    site_id: str
    id: str
    severity: str
    field_set: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class MicroSiteObservation:
    site_id: str
    site_name: str
    parent_region: str
    ava: str | None
    kind: str
    ordinal: int
    fields: Mapping[str, Any]
    source_refs: tuple[str, ...]

    @property
    def block_id(self) -> str | None:
        raw = self.fields.get("block")
        return str(raw) if raw is not None else None

    @property
    def variety(self) -> str | None:
        raw = self.fields.get("variety")
        return str(raw) if raw is not None else None

    @property
    def clone(self) -> str | None:
        raw = self.fields.get("clone")
        return str(raw) if raw is not None else None

    @property
    def rootstock(self) -> str | None:
        raw = self.fields.get("rootstock")
        return str(raw) if raw is not None else None


@dataclass(frozen=True)
class SiteResearchRecord:
    id: str
    name: str
    parent_region: str
    ava: str | None
    source_refs: tuple[str, ...]
    site_fields: Mapping[str, Any]
    observations: tuple[MicroSiteObservation, ...]
    quality_flags: tuple[SiteDataQualityFlag, ...]

    def observations_of_kind(self, kind: str) -> tuple[MicroSiteObservation, ...]:
        key = normalize_name(kind)
        return tuple(obs for obs in self.observations if normalize_name(obs.kind) == key)


@dataclass(frozen=True)
class SiteResearchStats:
    site_count: int
    referenced_source_count: int
    exact_block_count: int
    observation_count: int
    quality_flag_count: int
    ava_count: int


class SiteResearchRegistry:
    """Load source-stated vineyard and block observations without legal promotion."""

    RESTRICTED_AUTHORITY_CLAIMS = frozenset(
        normalize_name(value)
        for value in (
            "ava_legal_boundary",
            "protected_origin_legal_status",
            "legal_site_claim",
            "authorized_grape_legality",
            "universal_terroir_sensory_rule",
        )
    )

    OBSERVATION_KEYS: tuple[tuple[str, str], ...] = (
        ("blocks", "exact_block"),
        ("zones", "zone"),
        ("blockObservations", "block_observation"),
        ("contractedParcels", "contracted_parcel"),
        ("cloneBySiteObservations", "clone_by_site_observation"),
        ("vintageTechnicalObservations", "vintage_technical_observation"),
    )

    STRUCTURAL_SITE_KEYS = frozenset(
        {
            "id",
            "name",
            "parentRegion",
            "ava",
            "sourceRefs",
            "blocks",
            "zones",
            "blockObservations",
            "contractedParcels",
            "cloneBySiteObservations",
            "vintageTechnicalObservations",
            "dataQualityFlags",
        }
    )

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.sources: tuple[SiteResearchSource, ...] = ()
        self.sites: tuple[SiteResearchRecord, ...] = ()
        self._all_sources: dict[str, SiteResearchSource] = {}
        self._site_index: dict[str, SiteResearchRecord] = {}
        self._load_sources()
        self._load_sites()

    def _load_sources(self) -> None:
        all_sources: dict[str, SiteResearchSource] = {}
        files = _ordered_files("sources_pass")
        if not files:
            raise SiteResearchError(f"No site-research source registries found in {self.data_dir}")

        for path in files:
            doc = json.loads(path.read_text(encoding="utf-8"))
            for raw in doc.get("sources", []):
                source_id = str(raw.get("id", "")).strip()
                if not source_id:
                    raise SiteResearchError(f"Missing source id in {path.name}")
                if source_id in all_sources:
                    raise SiteResearchError(f"Duplicate site-research source id {source_id}")
                url = str(raw.get("url", "")).strip()
                if not url.startswith(("https://", "http://")):
                    raise SiteResearchError(f"Source {source_id} lacks an absolute URL")
                source = SiteResearchSource(
                    id=source_id,
                    publisher=str(raw.get("publisher", "")).strip(),
                    title=str(raw.get("title", "")).strip(),
                    url=url,
                    jurisdiction=str(raw.get("jurisdiction", "")).strip(),
                    kind=str(raw.get("kind", "")).strip(),
                    accessed=str(raw.get("accessed", "")).strip(),
                )
                if not source.publisher or not source.title or not source.kind:
                    raise SiteResearchError(f"Incomplete source metadata for {source_id}")
                all_sources[source_id] = source
        self._all_sources = all_sources

    def _load_sites(self) -> None:
        records: list[SiteResearchRecord] = []
        seen: set[str] = set()
        referenced_source_ids: set[str] = set()
        files = _ordered_files("willamette_micro_sites")
        if not files:
            raise SiteResearchError(f"No micro-site files found in {self.data_dir}")

        for path in files:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("schemaVersion") != 1:
                raise SiteResearchError(f"Unsupported micro-site schema in {path.name}")
            for raw in doc.get("sites", []):
                site_id = str(raw.get("id", "")).strip()
                if not site_id or site_id in seen:
                    raise SiteResearchError(f"Missing or duplicate site id {site_id!r}")
                name = str(raw.get("name", "")).strip()
                parent_region = str(raw.get("parentRegion", "")).strip()
                source_refs = tuple(str(ref) for ref in raw.get("sourceRefs", []))
                if not name or not parent_region or not source_refs:
                    raise SiteResearchError(f"Incomplete site identity/provenance for {site_id}")
                for source_ref in source_refs:
                    if source_ref not in self._all_sources:
                        raise SiteResearchError(
                            f"Site {site_id} references unknown source {source_ref}"
                        )
                    referenced_source_ids.add(source_ref)

                ava_raw = raw.get("ava")
                ava = str(ava_raw).strip() if ava_raw is not None else None
                observations: list[MicroSiteObservation] = []
                for raw_key, kind in self.OBSERVATION_KEYS:
                    values = raw.get(raw_key, [])
                    if values is None:
                        continue
                    if not isinstance(values, list):
                        raise SiteResearchError(f"{site_id}.{raw_key} must be a list")
                    for ordinal, value in enumerate(values, start=1):
                        if not isinstance(value, dict) or not value:
                            raise SiteResearchError(
                                f"{site_id}.{raw_key}[{ordinal}] must be a nonempty object"
                            )
                        observations.append(
                            MicroSiteObservation(
                                site_id=site_id,
                                site_name=name,
                                parent_region=parent_region,
                                ava=ava,
                                kind=kind,
                                ordinal=ordinal,
                                fields=_freeze(value),
                                source_refs=source_refs,
                            )
                        )

                quality_flags: list[SiteDataQualityFlag] = []
                for raw_flag in raw.get("dataQualityFlags", []):
                    flag_id = str(raw_flag.get("id", "")).strip()
                    detail = str(raw_flag.get("detail", "")).strip()
                    if not flag_id or not detail:
                        raise SiteResearchError(f"Incomplete data-quality flag on {site_id}")
                    quality_flags.append(
                        SiteDataQualityFlag(
                            site_id=site_id,
                            id=flag_id,
                            severity=str(raw_flag.get("severity", "unspecified")).strip(),
                            field_set=tuple(str(v) for v in raw_flag.get("fieldSet", [])),
                            detail=detail,
                        )
                    )

                site_fields = {
                    key: value
                    for key, value in raw.items()
                    if key not in self.STRUCTURAL_SITE_KEYS
                }
                record = SiteResearchRecord(
                    id=site_id,
                    name=name,
                    parent_region=parent_region,
                    ava=ava,
                    source_refs=source_refs,
                    site_fields=_freeze(site_fields),
                    observations=tuple(observations),
                    quality_flags=tuple(quality_flags),
                )
                records.append(record)
                self._site_index[site_id] = record
                seen.add(site_id)

        self.sites = tuple(records)
        self.sources = tuple(
            self._all_sources[source_id]
            for source_id in sorted(referenced_source_ids)
        )

    def source(self, source_id: str) -> SiteResearchSource | None:
        return self._all_sources.get(source_id)

    def site(self, site_id: str) -> SiteResearchRecord | None:
        return self._site_index.get(site_id)

    def by_name(self, name: str) -> tuple[SiteResearchRecord, ...]:
        key = normalize_name(name)
        return tuple(site for site in self.sites if normalize_name(site.name) == key)

    def observations(
        self,
        site_id: str,
        *,
        kind: str | None = None,
    ) -> tuple[MicroSiteObservation, ...]:
        site = self.site(site_id)
        if site is None:
            return ()
        if kind is None:
            return site.observations
        return site.observations_of_kind(kind)

    def block_history(self, site_id: str, block_id: str) -> tuple[MicroSiteObservation, ...]:
        target = normalize_name(block_id)
        return tuple(
            observation
            for observation in self.observations(site_id)
            if observation.kind in {"exact_block", "block_observation"}
            and observation.block_id is not None
            and normalize_name(observation.block_id) == target
        )

    def quality_flags(self, site_id: str | None = None) -> tuple[SiteDataQualityFlag, ...]:
        if site_id is None:
            return tuple(flag for site in self.sites for flag in site.quality_flags)
        site = self.site(site_id)
        return site.quality_flags if site is not None else ()

    def stats(self) -> SiteResearchStats:
        observations = [obs for site in self.sites for obs in site.observations]
        return SiteResearchStats(
            site_count=len(self.sites),
            referenced_source_count=len(self.sources),
            exact_block_count=sum(obs.kind == "exact_block" for obs in observations),
            observation_count=len(observations),
            quality_flag_count=sum(len(site.quality_flags) for site in self.sites),
            ava_count=len({site.ava for site in self.sites if site.ava}),
        )

    def assert_can_establish(self, claim_kind: str) -> None:
        if normalize_name(claim_kind) in self.RESTRICTED_AUTHORITY_CLAIMS:
            raise SiteResearchError(
                f"Producer/grower site evidence cannot independently establish {claim_kind!r}. "
                "Use the appropriate legal or institutional authority layer."
            )


def load_site_research() -> SiteResearchRegistry:
    return SiteResearchRegistry()
