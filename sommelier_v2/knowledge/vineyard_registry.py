"""Expanded, provenance-aware vineyard and named-site registry.

This module extends the original world catalog without changing the legacy seed
format. It materializes only named sites that can be tied to a cited source.
Physical attributes stay unknown until a source states them for the specific site.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .catalog import normalize_name
from .expanded_catalog import NamedSite as _BaseNamedSite
from .expanded_catalog import WorldWineKnowledgeCatalog as _BaseWorldWineKnowledgeCatalog

DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class NamedSiteSource:
    id: str
    authority: str = ""
    url: str = ""
    checked: str | None = None
    scope: str = ""
    evidence_class: str = ""
    notes: str = ""


@dataclass(frozen=True)
class SiteOwnershipPeriod:
    owner: str
    from_year: int | None = None
    to_year: int | None = None
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class NamedSite(_BaseNamedSite):
    """Named-site identity plus optional sourced physical/cadastral detail.

    New dimensions default to unknown. They are evidence fields, not generated
    terroir priors, and must never be filled by copying appellation-level facts.
    """

    parent_site_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    elevation_min_m: float | None = None
    elevation_max_m: float | None = None
    slope_min_pct: float | None = None
    slope_max_pct: float | None = None
    aspect: str | None = None
    soil_terms: tuple[str, ...] = ()
    permitted_grapes: tuple[str, ...] = ()
    ownership_history: tuple[SiteOwnershipPeriod, ...] = ()
    effective_from: str | None = None
    effective_to: str | None = None
    geometry_source_id: str | None = None


def _float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _slug(value: str) -> str:
    return normalize_name(value).replace(" ", "-")


def _source_record(source_id: str, raw: object) -> NamedSiteSource:
    if isinstance(raw, str):
        return NamedSiteSource(id=source_id, url=raw)
    if isinstance(raw, Mapping):
        return NamedSiteSource(
            id=source_id,
            authority=str(raw.get("authority", "")),
            url=str(raw.get("url", "")),
            checked=str(raw["checked"]) if raw.get("checked") else None,
            scope=str(raw.get("scope", "")),
            evidence_class=str(raw.get("evidence_class", "")),
            notes=str(raw.get("notes", "")),
        )
    raise ValueError(f"Invalid named-site source definition: {source_id}")


def _ownership_periods(raw: object) -> tuple[SiteOwnershipPeriod, ...]:
    if not isinstance(raw, list):
        return ()
    rows: list[SiteOwnershipPeriod] = []
    for item in raw:
        if not isinstance(item, Mapping) or not item.get("owner"):
            continue
        rows.append(
            SiteOwnershipPeriod(
                owner=str(item["owner"]),
                from_year=_int(item.get("from_year")),
                to_year=_int(item.get("to_year")),
                source_ids=tuple(str(v) for v in item.get("source_ids", [])),
            )
        )
    return tuple(rows)


def _site_from_values(*, raw: Mapping[str, object], defaults: Mapping[str, object], name: str) -> NamedSite:
    def value(key: str, fallback: object = None) -> object:
        return raw.get(key, defaults.get(key, fallback))

    id_prefix = str(value("id_prefix", "") or "")
    if raw.get("id"):
        site_id = str(raw["id"])
    elif id_prefix:
        site_id = f"{id_prefix}:{_slug(name)}"
    else:
        # Site type is part of identity. The same legal spelling can legitimately
        # occur under one appellation as both a classified climat and a village
        # lieu-dit. Omitting site_type caused the validator to collapse those
        # distinct records in the legacy seed.
        site_id = "site:" + ":".join(
            _slug(str(v))
            for v in (
                value("country", ""),
                value("region", ""),
                value("parent", ""),
                value("site_type", "named_site"),
                name,
            )
            if v
        )

    source_ids = tuple(str(v) for v in value("source_ids", []) or [])
    return NamedSite(
        id=site_id,
        name=name,
        country=str(value("country", "")),
        region=str(value("region", "")),
        site_type=str(value("site_type", "named_site")),
        parent=str(value("parent")) if value("parent") is not None else None,
        commune=str(value("commune")) if value("commune") is not None else None,
        classification=str(value("classification")) if value("classification") is not None else None,
        legal_status=str(value("legal_status", "documented_named_site")),
        owner=str(value("owner")) if value("owner") is not None else None,
        area_ha=_float(value("area_ha")),
        row_count=_int(value("row_count")),
        aliases=tuple(str(v) for v in value("aliases", []) or []),
        source_ids=source_ids,
        notes=str(value("notes", "")),
        parent_site_id=str(value("parent_site_id")) if value("parent_site_id") is not None else None,
        latitude=_float(value("latitude")),
        longitude=_float(value("longitude")),
        elevation_min_m=_float(value("elevation_min_m")),
        elevation_max_m=_float(value("elevation_max_m")),
        slope_min_pct=_float(value("slope_min_pct")),
        slope_max_pct=_float(value("slope_max_pct")),
        aspect=str(value("aspect")) if value("aspect") is not None else None,
        soil_terms=tuple(str(v) for v in value("soil_terms", []) or []),
        permitted_grapes=tuple(str(v) for v in value("permitted_grapes", []) or []),
        ownership_history=_ownership_periods(value("ownership_history", [])),
        effective_from=str(value("effective_from")) if value("effective_from") is not None else None,
        effective_to=str(value("effective_to")) if value("effective_to") is not None else None,
        geometry_source_id=str(value("geometry_source_id")) if value("geometry_source_id") is not None else None,
    )


def _load_site_document(path: Path) -> tuple[list[NamedSite], dict[str, NamedSiteSource], dict[str, dict[str, object]]]:
    if not path.exists():
        return [], {}, {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise ValueError(f"{path.name} must contain a JSON object")

    sources = {
        str(source_id): _source_record(str(source_id), raw)
        for source_id, raw in dict(doc.get("sources", {})).items()
    }
    bulk_sources = {
        str(source_id): dict(raw)
        for source_id, raw in dict(doc.get("bulk_sources_discovered", {})).items()
        if isinstance(raw, Mapping)
    }

    sites: list[NamedSite] = []
    for group in doc.get("groups", []):
        if not isinstance(group, Mapping):
            continue
        raw_names = group.get("names", [])
        if isinstance(raw_names, str):
            names = [value.strip() for value in raw_names.split("|") if value.strip()]
        else:
            names = [str(value).strip() for value in raw_names if str(value).strip()]
        for name in names:
            sites.append(_site_from_values(raw={}, defaults=group, name=name))

    for row in doc.get("records", []):
        if not isinstance(row, Mapping) or not row.get("name"):
            continue
        sites.append(_site_from_values(raw=row, defaults={}, name=str(row["name"])))

    return sites, sources, bulk_sources


def _load_registry_documents(paths: tuple[Path, ...]) -> tuple[
    list[NamedSite], dict[str, NamedSiteSource], dict[str, dict[str, object]], set[str]
]:
    sites: list[NamedSite] = []
    sources: dict[str, NamedSiteSource] = {}
    bulk_sources: dict[str, dict[str, object]] = {}
    expansion_source_ids: set[str] = set()

    for path in paths:
        rows, file_sources, file_bulk = _load_site_document(path)
        for source_id, source in file_sources.items():
            existing = sources.get(source_id)
            if existing is not None and existing != source:
                raise ValueError(f"Conflicting named-site source definition: {source_id}")
            sources[source_id] = source
        for source_id, raw in file_bulk.items():
            existing = bulk_sources.get(source_id)
            if existing is not None and existing != raw:
                raise ValueError(f"Conflicting named-site bulk source: {source_id}")
            bulk_sources[source_id] = raw
        sites.extend(rows)
        if path.name.startswith("named_sites_expansion_2026_") and path.name != "named_sites_expansion_2026_sources.json":
            expansion_source_ids.update(file_sources)

    for site in sites:
        missing = [source_id for source_id in site.source_ids if source_id not in sources]
        if missing:
            raise ValueError(f"{site.id} references unknown named-site sources: {missing}")
        if site.geometry_source_id and site.geometry_source_id not in sources:
            raise ValueError(f"{site.id} references unknown geometry source: {site.geometry_source_id}")
        for ownership in site.ownership_history:
            unknown = [source_id for source_id in ownership.source_ids if source_id not in sources]
            if unknown:
                raise ValueError(f"{site.id} ownership history references unknown sources: {unknown}")

    unique: dict[str, NamedSite] = {}
    for site in sites:
        existing = unique.get(site.id)
        if existing is not None and existing != site:
            raise ValueError(f"Conflicting named-site ID: {site.id}")
        unique[site.id] = site
    return (
        sorted(unique.values(), key=lambda row: (row.country, row.region, row.parent or "", row.site_type, row.name.casefold())),
        sources,
        bulk_sources,
        expansion_source_ids,
    )


class WorldWineKnowledgeCatalog(_BaseWorldWineKnowledgeCatalog):
    """World catalog with additive, source-validated named-site expansion."""

    def __init__(self) -> None:
        super().__init__()

        seed_path = DATA_DIR / "named_sites_seed.json"
        expansion_paths = tuple(sorted(DATA_DIR.glob("named_sites_expansion_2026_*.json")))
        all_paths = (seed_path, *expansion_paths)
        _, sources, bulk_sources, expansion_source_ids = _load_registry_documents(all_paths)

        expansion_only, _, _, _ = _load_registry_documents(expansion_paths)
        by_id: dict[str, NamedSite] = {site.id: site for site in self.named_sites}
        for site in expansion_only:
            existing = by_id.get(site.id)
            if existing is not None and existing != site:
                raise ValueError(f"Expansion conflicts with existing named-site ID: {site.id}")
            by_id[site.id] = site

        self.named_sites = sorted(
            by_id.values(),
            key=lambda row: (row.country, row.region, row.parent or "", row.site_type, row.name.casefold()),
        )
        self.named_site_sources = sources
        self.named_site_bulk_sources = bulk_sources
        self._named_site_expansion_source_ids = expansion_source_ids

    def sites(
        self,
        *,
        country: str | None = None,
        region: str | None = None,
        parent: str | None = None,
        site_type: str | None = None,
    ) -> list[NamedSite]:
        rows = self.named_sites
        if country is not None:
            rows = [row for row in rows if normalize_name(row.country) == normalize_name(country)]
        if region is not None:
            rows = [row for row in rows if normalize_name(row.region) == normalize_name(region)]
        if parent is not None:
            rows = [row for row in rows if normalize_name(row.parent or "") == normalize_name(parent)]
        if site_type is not None:
            rows = [row for row in rows if row.site_type == site_type]
        return rows

    def stats(self) -> dict[str, int]:
        stats = super().stats()
        expansion_ids = self._named_site_expansion_source_ids
        stats.update({
            "named_sites": len(self.named_sites),
            "named_site_types": len({site.site_type for site in self.named_sites}),
            "named_site_countries": len({site.country for site in self.named_sites if site.country}),
            "named_site_parents": len({(site.country, site.region, site.parent) for site in self.named_sites if site.parent}),
            "named_site_sources": len(self.named_site_sources),
            "named_site_bulk_sources_discovered": len(self.named_site_bulk_sources),
            "named_sites_2026_expansion": sum(
                1 for site in self.named_sites if any(source_id in expansion_ids for source_id in site.source_ids)
            ),
            "named_sites_with_owner": sum(site.owner is not None for site in self.named_sites),
            "named_sites_with_area": sum(site.area_ha is not None for site in self.named_sites),
            "named_sites_with_coordinates": sum(site.latitude is not None and site.longitude is not None for site in self.named_sites),
            "named_sites_with_elevation": sum(site.elevation_min_m is not None or site.elevation_max_m is not None for site in self.named_sites),
            "named_sites_with_slope": sum(site.slope_min_pct is not None or site.slope_max_pct is not None for site in self.named_sites),
            "named_sites_with_soil_terms": sum(bool(site.soil_terms) for site in self.named_sites),
            "named_sites_with_permitted_grapes": sum(bool(site.permitted_grapes) for site in self.named_sites),
            "named_sites_with_ownership_history": sum(bool(site.ownership_history) for site in self.named_sites),
            "monopoles": sum(site.site_type == "monopole" for site in self.named_sites),
            "producer_blocks": sum(site.site_type == "block" for site in self.named_sites),
        })
        return stats
