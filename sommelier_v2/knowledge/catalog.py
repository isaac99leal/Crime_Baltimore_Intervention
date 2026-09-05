"""Wine knowledge catalog and legacy-data migration."""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .schema import (
    Confidence,
    CoverageLevel,
    GeographicIndication,
    GrapeKnowledge,
    NumericRange,
    SensoryProfile,
    SourceRef,
    ViticultureProfile,
)

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
REPO_ROOT = PACKAGE_DIR.parents[1]
LEGACY_DATA_DIR = REPO_ROOT / "somm_simulator" / "data"


SOURCES: dict[str, SourceRef] = {
    "legacy_grapes": SourceRef(
        id="legacy_grapes",
        authority="Sommelier Simulator legacy catalog",
        title="Legacy grape profile catalog",
        url="repo:somm_simulator/data/grapes.json",
        retrieved_on="2026-09-05",
        confidence=Confidence.MEDIUM,
        notes="Existing project data; profile facts should be progressively re-sourced.",
    ),
    "legacy_regions": SourceRef(
        id="legacy_regions",
        authority="Sommelier Simulator legacy catalog",
        title="Legacy region hierarchy",
        url="repo:somm_simulator/data/regions.json",
        retrieved_on="2026-09-05",
        confidence=Confidence.MEDIUM,
        notes="Geographic hierarchy does not reliably distinguish legal GIs from informal geography.",
    ),
    "ttb_4_91": SourceRef(
        id="ttb_4_91",
        authority="U.S. Alcohol and Tobacco Tax and Trade Bureau / eCFR",
        title="27 CFR 4.91 — approved grape variety names",
        url="https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-4/subpart-J/section-4.91",
        retrieved_on="2026-09-05",
        confidence=Confidence.AUTHORITATIVE,
    ),
    "ttb_admin_grapes": SourceRef(
        id="ttb_admin_grapes",
        authority="U.S. Alcohol and Tobacco Tax and Trade Bureau",
        title="Administratively approved grape variety names",
        url="https://www.ttb.gov/regulated-commodities/beverage-alcohol/wine/grape-variety-designations-on-american-wine-labels",
        retrieved_on="2026-09-05",
        confidence=Confidence.AUTHORITATIVE,
    ),
    "ttb_avas": SourceRef(
        id="ttb_avas",
        authority="U.S. Alcohol and Tobacco Tax and Trade Bureau",
        title="Established American Viticultural Areas",
        url="https://www.ttb.gov/regulated-commodities/beverage-alcohol/wine/established-avas",
        retrieved_on="2026-09-05",
        confidence=Confidence.AUTHORITATIVE,
    ),
    "wine_australia_gis": SourceRef(
        id="wine_australia_gis",
        authority="Wine Australia",
        title="Register of protected Australian geographical indications",
        url="https://www.wineaustralia.com/labelling/register-of-protected-gis-and-other-terms/geographical-indications",
        retrieved_on="2026-09-05",
        confidence=Confidence.AUTHORITATIVE,
    ),
    "iponz_wine_gis": SourceRef(
        id="iponz_wine_gis",
        authority="Intellectual Property Office of New Zealand",
        title="New Zealand wine geographical indications register",
        url="https://www.iponz.govt.nz/get-ip/geographical-indications/register/?location=nz&type=wine",
        retrieved_on="2026-09-05",
        confidence=Confidence.AUTHORITATIVE,
    ),
}


def normalize_name(value: str) -> str:
    """Normalize a catalog name for identity matching, not display."""
    text = unicodedata.normalize("NFKD", value).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("’", "'").replace("·", "").replace("–", "-").replace("—", "-")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _load_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _designation_parts(line: str) -> tuple[str, list[str]]:
    """Split `Prime (Alias, Alias)` into a prime name and synonyms."""
    m = re.fullmatch(r"\s*(.*?)\s*(?:\((.*?)\))?\s*", line)
    if not m:
        return line.strip(), []
    primary = m.group(1).strip()
    aliases = []
    if m.group(2):
        aliases = [item.strip() for item in m.group(2).split(",") if item.strip()]
    return primary, aliases


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, item: str) -> None:
        if item and item not in self.parent:
            self.parent[item] = item

    def find(self, item: str) -> str:
        self.add(item)
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != item:
            nxt = self.parent[item]
            self.parent[item] = root
            item = nxt
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def groups(self) -> dict[str, set[str]]:
        out: dict[str, set[str]] = defaultdict(set)
        for item in self.parent:
            out[self.find(item)].add(item)
        return out


def _profile_number(profile: dict, key: str) -> float | None:
    value = profile.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _map_word_index(value: str | None) -> float | None:
    if not value:
        return None
    return {
        "very low": 0.1,
        "low": 0.25,
        "moderate": 0.5,
        "medium": 0.5,
        "high": 0.75,
        "very high": 0.9,
        "exceptional": 1.0,
    }.get(str(value).casefold())


def _legacy_grape_to_knowledge(raw: dict) -> GrapeKnowledge:
    profile = raw.get("typical_profile", {})
    vit = raw.get("viticulture", {})
    alcohol = profile.get("alcohol_range")
    if isinstance(alcohol, dict):
        alcohol_range = NumericRange(
            low=alcohol.get("low"), high=alcohol.get("high"), unit="% abv"
        )
    elif isinstance(alcohol, list) and len(alcohol) >= 2:
        alcohol_range = NumericRange(low=alcohol[0], high=alcohol[1], unit="% abv")
    else:
        alcohol_range = NumericRange(unit="% abv")

    return GrapeKnowledge(
        id="grape:" + normalize_name(raw["name"]).replace(" ", "-"),
        name=raw["name"],
        aliases=list(raw.get("aliases", [])),
        color=raw.get("color"),
        species="Vitis vinifera" if not raw.get("is_hybrid") else None,
        origin_country=raw.get("origin_country") or None,
        origin_region=raw.get("origin_region") or None,
        coverage=CoverageLevel.LEGACY_MIGRATED,
        confidence=Confidence.MEDIUM,
        viticulture=ViticultureProfile(
            vigor_index=_map_word_index(vit.get("vigor")),
            drought_tolerance=_map_word_index(vit.get("drought_tolerance")),
            preferred_climates=list(vit.get("climate_preferences", [])),
            rootstock_notes=list(vit.get("typical_rootstocks", [])),
        ),
        sensory=SensoryProfile(
            acidity=_profile_number(profile, "acidity"),
            tannin=_profile_number(profile, "tannin"),
            body=_profile_number(profile, "body"),
            sweetness=_profile_number(profile, "sweetness"),
            alcohol_pct=alcohol_range,
            fruit_intensity=_profile_number(profile, "fruit_intensity"),
            earth_intensity=_profile_number(profile, "earth_intensity"),
            oak_affinity=_profile_number(profile, "oak_affinity"),
            primary_aromas=list(raw.get("primary_aromas", [])),
            secondary_aromas=list(raw.get("secondary_aromas", [])),
            tertiary_aromas=list(raw.get("tertiary_aromas", [])),
        ),
        key_regions=list(raw.get("key_regions", [])),
        blending_partners=list(raw.get("blending_partners", [])),
        source_ids=["legacy_grapes"],
        tags={
            tag for tag, enabled in {
                "indigenous": raw.get("is_indigenous"),
                "international": raw.get("is_international"),
                "hybrid": raw.get("is_hybrid"),
                "table_grape": raw.get("is_table_grape"),
                "endangered": raw.get("endangered"),
                "sparkling_suitable": raw.get("winemaking", {}).get("sparkling_suitable"),
                "skin_contact_suitable": raw.get("winemaking", {}).get("skin_contact_suitable"),
                "amphora_suitable": raw.get("winemaking", {}).get("amphora_suitable"),
            }.items() if enabled
        },
        legacy_payload=raw,
    )


class WineKnowledgeCatalog:
    """Merged catalog with provenance-aware factual and simulation data."""

    def __init__(
        self,
        *,
        legacy_grapes_path: Path | None = None,
        legacy_regions_path: Path | None = None,
    ) -> None:
        self.legacy_grapes_path = legacy_grapes_path or LEGACY_DATA_DIR / "grapes.json"
        self.legacy_regions_path = legacy_regions_path or LEGACY_DATA_DIR / "regions.json"
        self.sources = dict(SOURCES)

        self.legacy_grape_records: list[dict] = []
        self.grapes: list[GrapeKnowledge] = []
        self.grape_alias_index: dict[str, GrapeKnowledge] = {}
        self.legacy_geographies: list[GeographicIndication] = []
        self.legal_gis: list[GeographicIndication] = []

        self._legacy_identity_roots: set[str] = set()
        self._load_grapes()
        self._load_legacy_geographies()
        self._load_legal_gis()

    def _load_grapes(self) -> None:
        raw_doc = json.loads(self.legacy_grapes_path.read_text(encoding="utf-8"))
        self.legacy_grape_records = list(raw_doc.get("grapes", []))

        uf = _UnionFind()
        display_names: dict[str, str] = {}
        legacy_primary_norms: set[str] = set()
        source_for_norm: dict[str, set[str]] = defaultdict(set)

        def add_identity(primary: str, aliases: Iterable[str], source_id: str) -> None:
            p = normalize_name(primary)
            if not p:
                return
            uf.add(p)
            display_names.setdefault(p, primary)
            source_for_norm[p].add(source_id)
            for alias in aliases:
                a = normalize_name(alias)
                if not a:
                    continue
                uf.add(a)
                display_names.setdefault(a, alias)
                source_for_norm[a].add(source_id)
                uf.union(p, a)

        for raw in self.legacy_grape_records:
            primary = raw.get("name", "")
            add_identity(primary, raw.get("aliases", []), "legacy_grapes")
            if primary:
                legacy_primary_norms.add(normalize_name(primary))

        official_files = [
            ("ttb_4_91", DATA_DIR / "ttb_approved_grape_designations.txt"),
            ("ttb_admin_grapes", DATA_DIR / "ttb_administrative_grape_designations.txt"),
        ]
        for source_id, path in official_files:
            for line in _load_lines(path):
                primary, aliases = _designation_parts(line)
                add_identity(primary, aliases, source_id)

        groups = uf.groups()
        root_for = {member: root for root, members in groups.items() for member in members}
        self._legacy_identity_roots = {root_for[n] for n in legacy_primary_norms if n in root_for}

        legacy_by_root: dict[str, list[dict]] = defaultdict(list)
        for raw in self.legacy_grape_records:
            n = normalize_name(raw.get("name", ""))
            if n in root_for:
                legacy_by_root[root_for[n]].append(raw)

        for root, members in groups.items():
            legacy_rows = legacy_by_root.get(root, [])
            if legacy_rows:
                raw = max(legacy_rows, key=lambda r: len(json.dumps(r, ensure_ascii=False)))
                grape = _legacy_grape_to_knowledge(raw)
            else:
                preferred = min(
                    members,
                    key=lambda n: (
                        0 if "ttb_4_91" in source_for_norm[n] else 1,
                        len(display_names.get(n, n)),
                        display_names.get(n, n).casefold(),
                    ),
                )
                grape = GrapeKnowledge(
                    id="grape:" + preferred.replace(" ", "-"),
                    name=display_names.get(preferred, preferred),
                    coverage=CoverageLevel.IDENTITY,
                    confidence=Confidence.AUTHORITATIVE,
                )

            names = sorted(
                {display_names.get(n, n) for n in members if display_names.get(n, n)},
                key=str.casefold,
            )
            grape.aliases = [n for n in names if normalize_name(n) != normalize_name(grape.name)]
            grape.source_ids = sorted(
                {
                    source_id
                    for member in members
                    for source_id in source_for_norm.get(member, set())
                }
                | set(grape.source_ids)
            )
            self.grapes.append(grape)
            for name in [grape.name, *grape.aliases]:
                self.grape_alias_index[normalize_name(name)] = grape

        self.grapes.sort(key=lambda g: g.name.casefold())

    def _load_legacy_geographies(self) -> None:
        doc = json.loads(self.legacy_regions_path.read_text(encoding="utf-8"))
        rows: list[GeographicIndication] = []
        for country in doc.get("regions", []):
            country_name = country.get("country", "")
            for region in country.get("wine_regions", []):
                r_path = [country_name, region.get("name", "")]
                rows.append(self._legacy_geo(country_name, "wine_region", r_path))
                for sub in region.get("sub_regions", []):
                    s_path = [*r_path, sub.get("name", "")]
                    rows.append(self._legacy_geo(country_name, "sub_region", s_path))
                    for commune in sub.get("communes", []):
                        c_path = [*s_path, commune.get("name", "")]
                        rows.append(self._legacy_geo(country_name, "commune_or_appellation", c_path))
        self.legacy_geographies = rows

    @staticmethod
    def _legacy_geo(country: str, kind: str, path: list[str]) -> GeographicIndication:
        key = "|".join(normalize_name(p) for p in path)
        return GeographicIndication(
            id="legacy-geo:" + key.replace(" ", "-"),
            name=path[-1],
            country=country,
            gi_type=kind,
            legal_status="unverified_legacy_geography",
            authority="Sommelier Simulator legacy catalog",
            source_ids=["legacy_regions"],
            coverage=CoverageLevel.LEGACY_MIGRATED,
            legacy_path=path,
        )

    def _load_legal_gis(self) -> None:
        specs = [
            ("United States", "American Viticultural Area", "ttb_avas", DATA_DIR / "us_avas.txt"),
            ("Australia", "Geographical Indication", "wine_australia_gis", DATA_DIR / "australia_gis.txt"),
            ("New Zealand", "Wine Geographical Indication", "iponz_wine_gis", DATA_DIR / "new_zealand_wine_gis.txt"),
        ]
        seen: set[tuple[str, str]] = set()
        legal: list[GeographicIndication] = []
        for country, gi_type, source_id, path in specs:
            for name in _load_lines(path):
                key = (normalize_name(country), normalize_name(name))
                if key in seen:
                    continue
                seen.add(key)
                legal.append(
                    GeographicIndication(
                        id="gi:" + key[0].replace(" ", "-") + ":" + key[1].replace(" ", "-"),
                        name=name,
                        country=country,
                        gi_type=gi_type,
                        legal_status="established_or_registered",
                        authority=self.sources[source_id].authority,
                        source_ids=[source_id],
                        coverage=CoverageLevel.IDENTITY,
                    )
                )
        self.legal_gis = sorted(legal, key=lambda gi: (gi.country, gi.name.casefold()))

    def grape(self, name_or_alias: str) -> GrapeKnowledge | None:
        return self.grape_alias_index.get(normalize_name(name_or_alias))

    def stats(self) -> dict[str, int]:
        legacy_designations = len(self.legacy_grape_records)
        merged = len(self.grapes)
        official_designations = (
            len(_load_lines(DATA_DIR / "ttb_approved_grape_designations.txt"))
            + len(_load_lines(DATA_DIR / "ttb_administrative_grape_designations.txt"))
        )
        return {
            "legacy_varietal_records": legacy_designations,
            "legacy_variety_identity_clusters": len(self._legacy_identity_roots),
            "official_grape_designations_ingested": official_designations,
            "merged_variety_identities": merged,
            "net_new_variety_identities": merged - len(self._legacy_identity_roots),
            "legacy_geographic_nodes": len(self.legacy_geographies),
            "explicit_legal_gis": len(self.legal_gis),
            "us_avas": sum(1 for gi in self.legal_gis if gi.country == "United States"),
            "australian_gis": sum(1 for gi in self.legal_gis if gi.country == "Australia"),
            "new_zealand_wine_gis": sum(1 for gi in self.legal_gis if gi.country == "New Zealand"),
        }
