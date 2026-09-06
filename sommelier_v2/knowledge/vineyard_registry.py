"""Expanded, provenance-aware vineyard and named-site registry.

The canonical catalog keeps site identity separate from legal label authority.
This module adds large, source-backed vineyard registries without changing that
rule: a mapped or listed site is evidence that the site exists, not permission
to put its name on a protected-origin wine.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

from .catalog import normalize_name
from .expanded_catalog import NamedSite as _BaseNamedSite
from .expanded_catalog import WorldWineKnowledgeCatalog as _BaseWorldWineKnowledgeCatalog

DATA_DIR = Path(__file__).resolve().parent / "data"

# These source classes carry stable source-defined record identities. Two rows
# with the same displayed vineyard name can still be different cadastral/legal
# units, so their explicit source IDs outrank a name-only semantic key.
RECORD_IDENTITY_EVIDENCE_CLASSES = frozenset(
    {
        "official_state_vineyard_registry_wfs",
        "official_vineyard_register_snapshot_pdf",
    }
)


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
    """Named-site identity plus optional, explicitly sourced physical detail."""

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
            url=str(raw.get("url") or raw.get("source_url") or ""),
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


def _site_from_values(
    *, raw: Mapping[str, object], defaults: Mapping[str, object], name: str
) -> NamedSite:
    def value(key: str, fallback: object = None) -> object:
        return raw.get(key, defaults.get(key, fallback))

    id_prefix = str(value("id_prefix", "") or "")
    if raw.get("id"):
        site_id = str(raw["id"])
    elif id_prefix:
        site_id = f"{id_prefix}:{_slug(name)}"
    else:
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
        source_ids=tuple(str(v) for v in value("source_ids", []) or []),
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


def _load_site_document(
    path: Path,
) -> tuple[list[NamedSite], dict[str, NamedSiteSource], dict[str, dict[str, object]]]:
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
            names = [item.strip() for item in raw_names.split("|") if item.strip()]
        else:
            names = [str(item).strip() for item in raw_names if str(item).strip()]
        for name in names:
            sites.append(_site_from_values(raw={}, defaults=group, name=name))

    for row in doc.get("records", []):
        if not isinstance(row, Mapping) or not row.get("name"):
            continue
        sites.append(_site_from_values(raw=row, defaults={}, name=str(row["name"])))
    return sites, sources, bulk_sources


def _load_registry_documents(
    paths: tuple[Path, ...],
) -> tuple[list[NamedSite], dict[str, NamedSiteSource], dict[str, dict[str, object]], set[str]]:
    sites: list[NamedSite] = []
    sources: dict[str, NamedSiteSource] = {}
    bulk_sources: dict[str, dict[str, object]] = {}
    materialized_source_ids: set[str] = set()

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
                raise ValueError(f"Conflicting named-site bulk-source definition: {source_id}")
            bulk_sources[source_id] = raw
        sites.extend(rows)
        if path.name != "vineyard_sites_2026_sources.json":
            materialized_source_ids.update(file_sources)

    for site in sites:
        missing = [source_id for source_id in site.source_ids if source_id not in sources]
        if missing:
            raise ValueError(f"{site.id} references unknown vineyard-site sources: {missing}")
        if site.geometry_source_id and site.geometry_source_id not in sources:
            raise ValueError(f"{site.id} references unknown geometry source: {site.geometry_source_id}")
        for period in site.ownership_history:
            unknown = [source_id for source_id in period.source_ids if source_id not in sources]
            if unknown:
                raise ValueError(f"{site.id} ownership history references unknown sources: {unknown}")

    unique_ids: dict[str, NamedSite] = {}
    for site in sites:
        existing = unique_ids.get(site.id)
        if existing is not None and existing != site:
            raise ValueError(f"Conflicting vineyard-site ID: {site.id}")
        unique_ids[site.id] = site

    return (
        sorted(
            unique_ids.values(),
            key=lambda row: (
                row.country,
                row.region,
                row.parent or "",
                row.site_type,
                row.name.casefold(),
            ),
        ),
        sources,
        bulk_sources,
        materialized_source_ids,
    )


def _promote(site: _BaseNamedSite) -> NamedSite:
    if isinstance(site, NamedSite):
        return site
    return NamedSite(
        id=site.id,
        name=site.name,
        country=site.country,
        region=site.region,
        site_type=site.site_type,
        parent=site.parent,
        commune=site.commune,
        classification=site.classification,
        legal_status=site.legal_status,
        owner=site.owner,
        area_ha=site.area_ha,
        row_count=site.row_count,
        aliases=tuple(site.aliases),
        source_ids=tuple(site.source_ids),
        notes=site.notes,
    )


def _semantic_key(site: _BaseNamedSite) -> tuple[str, str, str, str, str]:
    return (
        normalize_name(site.country),
        normalize_name(site.region),
        normalize_name(site.parent or ""),
        normalize_name(site.site_type),
        normalize_name(site.name),
    )


def _has_source_defined_identity(
    site: _BaseNamedSite,
    sources: Mapping[str, NamedSiteSource],
) -> bool:
    """Return whether a source explicitly makes the record ID identity-bearing."""
    return any(
        sources.get(source_id) is not None
        and sources[source_id].evidence_class in RECORD_IDENTITY_EVIDENCE_CLASSES
        for source_id in site.source_ids
    )


def _merge_identity_evidence(existing: NamedSite, donor: NamedSite) -> NamedSite:
    """Keep canonical identity facts while adding non-conflicting donor evidence."""
    kwargs: dict[str, object] = {
        "source_ids": tuple(dict.fromkeys((*existing.source_ids, *donor.source_ids))),
        "aliases": tuple(dict.fromkeys((*existing.aliases, *donor.aliases))),
    }
    for field_name in (
        "parent_site_id",
        "latitude",
        "longitude",
        "elevation_min_m",
        "elevation_max_m",
        "slope_min_pct",
        "slope_max_pct",
        "aspect",
        "effective_from",
        "effective_to",
        "geometry_source_id",
    ):
        if getattr(existing, field_name) is None and getattr(donor, field_name) is not None:
            kwargs[field_name] = getattr(donor, field_name)
    if not existing.soil_terms and donor.soil_terms:
        kwargs["soil_terms"] = donor.soil_terms
    if not existing.permitted_grapes and donor.permitted_grapes:
        kwargs["permitted_grapes"] = donor.permitted_grapes
    if not existing.ownership_history and donor.ownership_history:
        kwargs["ownership_history"] = donor.ownership_history
    return replace(existing, **kwargs)


def _load_canonical_source_ledger() -> dict[str, NamedSiteSource]:
    path = DATA_DIR / "named_site_sources.json"
    if not path.exists():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("sources", []) if isinstance(doc, Mapping) else []
    result: dict[str, NamedSiteSource] = {}
    for raw in rows:
        if not isinstance(raw, Mapping) or not raw.get("id"):
            continue
        source_id = str(raw["id"])
        result[source_id] = _source_record(source_id, raw)
    return result


class WorldWineKnowledgeCatalog(_BaseWorldWineKnowledgeCatalog):
    """World catalog with additive, source-validated named-vineyard expansion."""

    def __init__(self) -> None:
        super().__init__()

        expansion_paths = tuple(sorted(DATA_DIR.glob("vineyard_sites_2026_*.json")))
        expansion, sources, bulk_sources, expansion_source_ids = _load_registry_documents(
            expansion_paths
        )

        source_registry = dict(sources)
        for source_id, source in _load_canonical_source_ledger().items():
            source_registry.setdefault(source_id, source)

        # Canonical records define the preferred identity when an imported donor
        # describes the same ordinary named site. Source-defined registry rows are
        # different: their explicit IDs are part of the evidence and must survive
        # even when two records share a human-readable semantic key.
        by_identity_key: dict[tuple[object, ...], NamedSite] = {}

        def identity_key(site: NamedSite) -> tuple[object, ...]:
            if _has_source_defined_identity(site, source_registry):
                return ("source-record", site.id)
            return ("semantic", *_semantic_key(site))

        for raw in self.named_sites:
            site = _promote(raw)
            key = identity_key(site)
            existing = by_identity_key.get(key)
            if existing is None:
                by_identity_key[key] = site
            else:
                by_identity_key[key] = _merge_identity_evidence(existing, site)

        for donor in expansion:
            key = identity_key(donor)
            existing = by_identity_key.get(key)
            if existing is None:
                by_identity_key[key] = donor
            else:
                by_identity_key[key] = _merge_identity_evidence(existing, donor)

        self.named_sites = sorted(
            by_identity_key.values(),
            key=lambda row: (
                row.country,
                row.region,
                row.parent or "",
                row.site_type,
                row.name.casefold(),
                row.id,
            ),
        )

        self.named_site_sources = source_registry
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
            rows = [row for row in rows if normalize_name(row.site_type) == normalize_name(site_type)]
        return rows

    def stats(self) -> dict[str, int]:
        stats = super().stats()
        expansion_ids = self._named_site_expansion_source_ids
        stats.update(
            {
                "named_sites": len(self.named_sites),
                "named_site_types": len({site.site_type for site in self.named_sites}),
                "named_site_countries": len({site.country for site in self.named_sites if site.country}),
                "named_site_parents": len(
                    {
                        (site.country, site.region, site.parent)
                        for site in self.named_sites
                        if site.parent
                    }
                ),
                "named_site_sources": len(self.named_site_sources),
                "named_site_bulk_sources_discovered": len(self.named_site_bulk_sources),
                "named_sites_2026_expansion": sum(
                    1
                    for site in self.named_sites
                    if any(source_id in expansion_ids for source_id in site.source_ids)
                ),
                "named_sites_with_owner": sum(site.owner is not None for site in self.named_sites),
                "named_sites_with_area": sum(site.area_ha is not None for site in self.named_sites),
                "named_sites_with_coordinates": sum(
                    site.latitude is not None and site.longitude is not None
                    for site in self.named_sites
                ),
                "named_sites_with_elevation": sum(
                    site.elevation_min_m is not None or site.elevation_max_m is not None
                    for site in self.named_sites
                ),
                "named_sites_with_slope": sum(
                    site.slope_min_pct is not None or site.slope_max_pct is not None
                    for site in self.named_sites
                ),
                "named_sites_with_soil_terms": sum(bool(site.soil_terms) for site in self.named_sites),
                "named_sites_with_permitted_grapes": sum(
                    bool(site.permitted_grapes) for site in self.named_sites
                ),
                "named_sites_with_ownership_history": sum(
                    bool(site.ownership_history) for site in self.named_sites
                ),
                "monopoles": sum(site.site_type == "monopole" for site in self.named_sites),
                "producer_blocks": sum(site.site_type == "block" for site in self.named_sites),
            }
        )
        return stats
