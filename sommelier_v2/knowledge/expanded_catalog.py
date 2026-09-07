"""World-scale wine knowledge catalog built on the normalized v2 core.

The expanded catalog treats different evidence types separately:
- a census row is evidence that a variety name was reported in cultivation;
- a regulatory designation is evidence that a label name is legally accepted;
- a PIWI record is evidence of documented disease-resistant breeding/approval;
- a commercial observation is evidence that a named variety reached a market;
- none of those facts alone proves that two spellings are genetically distinct.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, replace
from collections import defaultdict
from hashlib import sha256
import unicodedata
from pathlib import Path
from typing import Iterable

from .catalog import WineKnowledgeCatalog, normalize_name
from .schema import Confidence, CoverageLevel, GeographicIndication, GrapeKnowledge

DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class VarietyAreaObservation:
    prime_name: str
    country: str | None = None
    area_2000_ha: float | None = None
    area_2010_ha: float | None = None
    area_2016_ha: float | None = None
    area_2023_ha: float | None = None
    source_id: str = "adelaide_2025"
    source_row: int | None = None
    country_as_reported: str | None = None

    @property
    def latest_positive_area_ha(self) -> float | None:
        for value in (self.area_2023_ha, self.area_2016_ha, self.area_2010_ha, self.area_2000_ha):
            if value is not None and value > 0:
                return value
        return None


@dataclass(frozen=True)
class PiwiRecord:
    name: str
    country: str
    status: str
    source_id: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class CommercialObservation:
    variety: str
    kind: str
    organization: str
    country: str
    producer: str | None = None
    wine: str | None = None
    vintage: str | None = None
    source_url: str = ""
    notes: str = ""


@dataclass(frozen=True)
class NamedSite:
    id: str
    name: str
    country: str
    region: str
    site_type: str
    parent: str | None = None
    commune: str | None = None
    classification: str | None = None
    legal_status: str = "documented_named_site"
    owner: str | None = None
    area_ha: float | None = None
    row_count: int | None = None
    aliases: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    notes: str = ""


def _float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _slug(value: str) -> str:
    return normalize_name(value).replace(" ", "-")


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _dedupe_sites(sites: Iterable[NamedSite]) -> list[NamedSite]:
    """Preserve stable IDs while retaining legally distinct colliding site identities."""
    unique: dict[str, NamedSite] = {}
    for site in sites:
        if not site.name:
            continue
        existing = unique.get(site.id)
        if existing is None:
            unique[site.id] = site
            continue
        if existing == site:
            continue

        base_collision_id = f"{site.id}:{_slug(site.site_type)}"
        collision_id = base_collision_id
        counter = 2
        while collision_id in unique and unique[collision_id] != site:
            collision_id = f"{base_collision_id}-{counter}"
            counter += 1
        unique.setdefault(collision_id, replace(site, id=collision_id))

    return sorted(
        unique.values(),
        key=lambda s: (
            s.country,
            s.region,
            s.parent or "",
            s.name.casefold(),
            s.site_type,
        ),
    )


def _load_sites(path: Path) -> list[NamedSite]:
    if not path.exists():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    sites: list[NamedSite] = []
    for group in doc.get("groups", []):
        for name in group.get("names", []):
            sites.append(
                NamedSite(
                    id="site:" + ":".join(
                        _slug(v) for v in (
                            group.get("country", ""), group.get("region", ""),
                            group.get("parent", ""), str(name),
                        ) if v
                    ),
                    name=str(name),
                    country=str(group.get("country", "")),
                    region=str(group.get("region", "")),
                    site_type=str(group.get("site_type", "named_site")),
                    parent=group.get("parent"),
                    commune=group.get("commune"),
                    classification=group.get("classification"),
                    legal_status=str(group.get("legal_status", "documented_named_site")),
                    source_ids=tuple(group.get("source_ids", [])),
                    notes=str(group.get("notes", "")),
                )
            )
    for row in doc.get("records", []):
        sites.append(
            NamedSite(
                id=str(row.get("id") or "site:" + ":".join(
                    _slug(v) for v in (
                        row.get("country", ""), row.get("region", ""),
                        row.get("parent", ""), row.get("name", ""),
                    ) if v
                )),
                name=str(row.get("name", "")),
                country=str(row.get("country", "")),
                region=str(row.get("region", "")),
                site_type=str(row.get("site_type", "named_site")),
                parent=row.get("parent"),
                commune=row.get("commune"),
                classification=row.get("classification"),
                legal_status=str(row.get("legal_status", "documented_named_site")),
                owner=row.get("owner"),
                area_ha=_float(row.get("area_ha")),
                row_count=int(row["row_count"]) if row.get("row_count") is not None else None,
                aliases=tuple(row.get("aliases", [])),
                source_ids=tuple(row.get("source_ids", [])),
                notes=str(row.get("notes", "")),
            )
        )
    return _dedupe_sites(sites)


class WorldWineKnowledgeCatalog:
    """Aggregate factual registry/census evidence around the v2 core catalog."""

    def __init__(self) -> None:
        self.base = WineKnowledgeCatalog()
        self.world_area: list[VarietyAreaObservation] = []
        self.country_area: list[VarietyAreaObservation] = []
        self.unresolved_country_area: list[VarietyAreaObservation] = []
        self.piwi_records: list[PiwiRecord] = []
        self.commercial_observations: list[CommercialObservation] = []
        self.eambrosia_gis: list[GeographicIndication] = []
        self.named_sites: list[NamedSite] = []
        self.grapes: list[GrapeKnowledge] = []
        self.grape_alias_index: dict[str, GrapeKnowledge] = {}
        self._load_area()
        self._load_piwi()
        self._load_commercial()
        self._load_eambrosia()
        site_rows: list[NamedSite] = []
        for path in sorted(DATA_DIR.glob("named_sites_*.json"), key=lambda item: item.name):
            site_rows.extend(_load_sites(path))
        self.named_sites = _dedupe_sites(site_rows)
        self._merge_grape_universe()

    def _load_area(self) -> None:
        for source_row, row in enumerate(_read_csv(DATA_DIR / "adelaide_world_varieties_2000_2023.csv"), 2):
            name = (row.get("prime") or "").strip()
            if not name:
                continue
            self.world_area.append(VarietyAreaObservation(
                prime_name=name, source_row=source_row,
                area_2000_ha=_float(row.get("area_2000_ha")),
                area_2010_ha=_float(row.get("area_2010_ha")),
                area_2016_ha=_float(row.get("area_2016_ha")),
                area_2023_ha=_float(row.get("area_2023_ha")),
            ))
        for source_row, row in enumerate(_read_csv(DATA_DIR / "adelaide_country_varieties_2000_2023.csv"), 2):
            name = (row.get("prime") or "").strip()
            country = (row.get("country") or "").strip()
            if not name:
                continue
            unresolved = not country or country.casefold().startswith("missing")
            target = self.unresolved_country_area if unresolved else self.country_area
            target.append(VarietyAreaObservation(
                prime_name=name, source_row=source_row, country_as_reported=country,
                country=None if unresolved else country,
                area_2000_ha=_float(row.get("area_2000_ha")),
                area_2010_ha=_float(row.get("area_2010_ha")),
                area_2016_ha=_float(row.get("area_2016_ha")),
                area_2023_ha=_float(row.get("area_2023_ha")),
            ))

    def _load_piwi(self) -> None:
        path = DATA_DIR / "piwi_registry.json"
        if not path.exists():
            return
        doc = json.loads(path.read_text(encoding="utf-8"))
        self.piwi_records = [
            PiwiRecord(
                name=str(row["name"]), country=str(row.get("country", "")),
                status=str(row.get("status", "documented_piwi")),
                source_id=str(row.get("source_id", "piwi_registry")),
                aliases=tuple(row.get("aliases", [])),
            )
            for row in doc.get("records", []) if row.get("name")
        ]

    def _load_commercial(self) -> None:
        path = DATA_DIR / "commercial_observations.json"
        if not path.exists():
            return
        doc = json.loads(path.read_text(encoding="utf-8"))
        self.commercial_observations = [
            CommercialObservation(
                variety=str(row["variety"]), kind=str(row.get("kind", "market_sighting")),
                organization=str(row.get("organization", "")), country=str(row.get("country", "")),
                producer=row.get("producer"), wine=row.get("wine"), vintage=row.get("vintage"),
                source_url=str(row.get("source_url", "")), notes=str(row.get("notes", "")),
            )
            for row in doc.get("records", []) if row.get("variety")
        ]

    def _load_eambrosia(self) -> None:
        path = DATA_DIR / "eambrosia_wine_gis.json"
        if not path.exists():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        rows: list[GeographicIndication] = []
        for item in raw:
            names = [str(name).strip() for name in item.get("protected_names", []) if str(name).strip()]
            if not names or item.get("removed"):
                continue
            countries = [str(c) for c in item.get("countries", [])]
            rows.append(GeographicIndication(
                id="gi:eambrosia:" + str(item.get("gi_identifier")),
                name=names[0], aliases=names[1:], country=";".join(countries),
                gi_type=str(item.get("gi_type") or "GI"),
                legal_status=str(item.get("status") or "registered"),
                authority="European Commission eAmbrosia",
                source_ids=["eambrosia"],
                established_date=item.get("eu_protection_date"),
                coverage=CoverageLevel.IDENTITY,
            ))
        self.eambrosia_gis = sorted(rows, key=lambda g: (g.country, g.name.casefold()))

    def _merge_grape_universe(self) -> None:
        # Source spellings are observation keys, not proof of botanical identity.
        # Preserve the established base catalog; never merge new names by folding
        # accents/punctuation, or let a later source overwrite an earlier alias.
        grapes = list(self.base.grapes)
        exact: dict[str, list[GrapeKnowledge]] = defaultdict(list)
        used_ids = {g.id for g in grapes}
        created_by_source: dict[tuple[str, str], GrapeKnowledge] = {}
        source_names: dict[str, set[str]] = defaultdict(set)
        for name in [*(r.prime_name for r in self.world_area),
                     *(r.name for r in self.piwi_records),
                     *(r.variety for r in self.commercial_observations)]:
            source_names[_slug(name)].add(unicodedata.normalize("NFC", name).strip().casefold())
        slug_owners = {key: min(names) for key, names in source_names.items()}

        def register(grape: GrapeKnowledge, names: Iterable[str]) -> None:
            for name in names:
                key = unicodedata.normalize("NFC", name).strip().casefold()
                if all(g.id != grape.id for g in exact[key]):
                    exact[key].append(grape)

        def lookup(name: str) -> GrapeKnowledge | None:
            rows = exact.get(unicodedata.normalize("NFC", name).strip().casefold(), [])
            return rows[0] if len(rows) == 1 else None

        def create(name: str, prefix: str, source_id: str) -> GrapeKnowledge:
            candidate_id = prefix + _slug(name)
            exact_key = unicodedata.normalize("NFC", name).strip().casefold()
            if (prefix, exact_key) in created_by_source:
                return created_by_source[(prefix, exact_key)]
            if candidate_id in used_ids or exact_key != slug_owners[_slug(name)]:
                candidate_id += ":" + sha256(exact_key.encode("utf-8")).hexdigest()[:12]
            if candidate_id in used_ids:
                raise ValueError(f"Duplicate observation identity: {name}")
            used_ids.add(candidate_id)
            grape = GrapeKnowledge(
                id=candidate_id, name=name, coverage=CoverageLevel.IDENTITY,
                confidence=Confidence.MEDIUM, source_ids=[source_id],
                tags={"unresolved_botanical_identity"},
            )
            grapes.append(grape)
            register(grape, [name])
            created_by_source[(prefix, exact_key)] = grape
            return grape

        for grape in grapes:
            register(grape, [grape.name, *grape.aliases])

        for obs in self.world_area:
            grape = lookup(obs.prime_name)
            if grape is None:
                grape = create(obs.prime_name, "grape:adelaide:", obs.source_id)
            if obs.source_id not in grape.source_ids:
                grape.source_ids.append(obs.source_id)
            grape.tags.add("census_prime_name")
            if obs.area_2023_ha is not None and obs.area_2023_ha > 0:
                grape.tags.add("commercial_cultivation_2023")
                if obs.area_2023_ha <= 1:
                    grape.tags.add("tiny_acreage_2023")
                if obs.area_2023_ha <= 5:
                    grape.tags.add("micro_acreage_2023")
            elif obs.latest_positive_area_ha is not None:
                grape.tags.add("historical_cultivation")

        def attach_observation(name: str, aliases: Iterable[str], tag: str, source_id: str) -> None:
            grape = lookup(name)
            if grape is None:
                grape = create(name, "grape:observed:", source_id)
            grape.tags.add(tag)
            if source_id not in grape.source_ids:
                grape.source_ids.append(source_id)
            # Aliases from PIWI/market records are search candidates only. They
            # cannot merge identities or replace aliases from another source.
            for alias in aliases:
                register(grape, [alias])

        for row in self.piwi_records:
            attach_observation(row.name, row.aliases, "piwi", row.source_id)
        for row in self.commercial_observations:
            attach_observation(row.variety, (), "commercial_market_observation", "commercial_observations")

        folded: dict[str, dict[str, GrapeKnowledge]] = defaultdict(dict)
        for spelling, rows in exact.items():
            for grape in rows:
                folded[normalize_name(spelling)][grape.id] = grape
        self.grapes = sorted(grapes, key=lambda g: (g.name.casefold(), g.id))
        self._grape_exact_index = exact
        self.grape_name_candidates = {key: tuple(rows.values()) for key, rows in folded.items()}
        # Compatibility index contains only unambiguous search keys.
        self.grape_alias_index = {key: rows[0] for key, rows in self.grape_name_candidates.items() if len(rows) == 1}

    def grape(self, name_or_alias: str) -> GrapeKnowledge | None:
        key = unicodedata.normalize("NFC", name_or_alias).strip().casefold()
        rows = self._grape_exact_index.get(key, [])
        if rows:
            return rows[0] if len(rows) == 1 else None
        return self.grape_alias_index.get(normalize_name(name_or_alias))

    def operational_variety(self, source_name: str):
        """Return the simulation-enabled operational record for a source variety."""
        from .variety_bulk import BulkVarietyRegistry
        if not hasattr(self, "_bulk_variety_registry"):
            self._bulk_variety_registry = BulkVarietyRegistry(catalog=self)
        return self._bulk_variety_registry.record(source_name)

    def assess_variety_country_plausibility(self, source_name: str, target_country: str):
        """Assess observed/commercial/agronomic planting plausibility without legal inference."""
        from .variety_bulk import BulkVarietyRegistry
        if not hasattr(self, "_bulk_variety_registry"):
            self._bulk_variety_registry = BulkVarietyRegistry(catalog=self)
        return self._bulk_variety_registry.assess_country_plausibility(source_name, target_country)

    def resolve_variety_identity(self, source_name: str, *, source_id: str = "adelaide_2025",
                                 country: str | None = None):
        """Resolve botanical evidence independently of profile/search matching."""
        from .variety_identity import VarietyIdentityRegistry
        if not hasattr(self, "_variety_identity_registry"):
            self._variety_identity_registry = VarietyIdentityRegistry()
        return self._variety_identity_registry.resolve(source_name, source_id=source_id, country=country)

    def area_for(self, name_or_alias: str, country: str | None = None) -> list[VarietyAreaObservation]:
        # Direct source spelling is useful even when botanical identity is unknown.
        # Do not let normalized search silently pool colliding census observations.
        def exact_key(name: str) -> str:
            return unicodedata.normalize("NFC", name).strip().casefold()
        accepted = {exact_key(name_or_alias)}
        grape = self.grape(name_or_alias)
        if grape is not None:
            accepted.update(exact_key(n) for n in [grape.name, *grape.aliases]
                            if self.grape(n) is grape)
        rows = self.country_area if country else self.world_area
        return [row for row in rows if exact_key(row.prime_name) in accepted
                and (country is None or normalize_name(row.country or "") == normalize_name(country))]

    def sites(self, *, region: str | None = None, site_type: str | None = None) -> list[NamedSite]:
        rows = self.named_sites
        if region is not None:
            rows = [row for row in rows if normalize_name(row.region) == normalize_name(region)]
        if site_type is not None:
            rows = [row for row in rows if row.site_type == site_type]
        return rows

    def stats(self) -> dict[str, int]:
        world_positive = [r for r in self.world_area if (r.area_2023_ha or 0) > 0]
        countries = {r.country for r in self.country_area if r.country}
        site_types = {s.site_type for s in self.named_sites}
        return {
            "base_grape_identities": len(self.base.grapes),
            "adelaide_world_prime_names": len(self.world_area),
            "adelaide_country_variety_observations": len(self.country_area),
            "adelaide_countries": len(countries),
            "adelaide_unresolved_country_observations": len(self.unresolved_country_area),
            "grape_ambiguous_search_keys": sum(len(rows) > 1 for rows in self.grape_name_candidates.values()),
            "adelaide_positive_area_2023": len(world_positive),
            "adelaide_tiny_le_1ha_2023": sum(1 for r in world_positive if (r.area_2023_ha or 0) <= 1),
            "adelaide_micro_le_5ha_2023": sum(1 for r in world_positive if (r.area_2023_ha or 0) <= 5),
            "combined_grape_identity_records": len(self.grapes),
            "piwi_registry_records": len(self.piwi_records),
            "commercial_observations": len(self.commercial_observations),
            "base_explicit_legal_gis": len(self.base.legal_gis),
            "eambrosia_wine_gis": len(self.eambrosia_gis),
            "combined_legal_gi_records_before_cross_registry_dedupe": len(self.base.legal_gis) + len(self.eambrosia_gis),
            "named_sites": len(self.named_sites),
            "named_site_types": len(site_types),
            "monopoles": sum(1 for s in self.named_sites if s.site_type == "monopole"),
            "producer_blocks": sum(1 for s in self.named_sites if s.site_type == "block"),
        }
