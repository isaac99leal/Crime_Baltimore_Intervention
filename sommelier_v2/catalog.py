"""Catalog bridge that reuses the existing large legacy wine data assets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .domain import WineRecord, WineStyle


_STYLE_MAP = {style.value.lower(): style for style in WineStyle}


def _style(value: str) -> WineStyle:
    return _STYLE_MAP.get((value or "").lower(), WineStyle.OTHER)


def from_legacy_wine(wine: object) -> WineRecord:
    profile = getattr(wine, "profile")
    region_path = list(getattr(wine, "region_path", []))
    grapes = tuple(getattr(g, "grape", str(g)) for g in getattr(wine, "grapes", []))
    aromas = tuple(list(getattr(profile, "primary_aromas", [])) + list(getattr(profile, "secondary_aromas", [])) + list(getattr(profile, "tertiary_aromas", [])))
    producer = getattr(wine, "producer_name", "") or getattr(wine, "estate_name", "")
    label = getattr(wine, "estate_name", "") or getattr(wine, "appellation", "")
    return WineRecord(
        id=str(getattr(wine, "id")), producer=producer, label=label,
        country=region_path[0] if region_path else "Unknown",
        region=region_path[1] if len(region_path) > 1 else (region_path[0] if region_path else "Unknown"),
        subregion=region_path[2] if len(region_path) > 2 else "",
        appellation=getattr(wine, "appellation", ""), vineyard=getattr(wine, "vineyard_name", ""),
        vintage=int(getattr(wine, "vintage", 0)), style=_style(getattr(wine, "style", "")), grapes=grapes,
        classification=getattr(wine, "classification", ""), wholesale_cost=float(getattr(wine, "wholesale_cost", 0.0)),
        rarity=float(getattr(wine, "rarity", 0.0)), acidity=float(getattr(profile, "acidity", 3.0)),
        tannin=float(getattr(profile, "tannin", 3.0)), body=float(getattr(profile, "body", 3.0)),
        sweetness=float(getattr(profile, "sweetness", 1.0)), alcohol=float(getattr(profile, "alcohol", 13.0)),
        fruit_intensity=float(getattr(profile, "fruit_intensity", 3.0)), earth_intensity=float(getattr(profile, "earth_intensity", 2.0)),
        oak_influence=float(getattr(profile, "oak_influence", 2.0)), aromas=aromas,
        winemaking_notes=getattr(wine, "winemaking_notes", ""), farming_notes=getattr(wine, "farming_notes", ""),
        drink_window_start=int(getattr(wine, "drink_window_start", 0)), drink_window_end=int(getattr(wine, "drink_window_end", 0)),
        is_organic=bool(getattr(wine, "is_organic", False)), is_biodynamic=bool(getattr(wine, "is_biodynamic", False)),
        is_natural=bool(getattr(wine, "is_natural", False)), is_ungrafted=bool(getattr(wine, "is_ungrafted", False)),
        is_old_vine=bool(getattr(wine, "is_old_vine", False)),
    )


def load_legacy_catalog(target_count: int = 10_000, seed: int = 42) -> list[WineRecord]:
    from somm_simulator.models.region import RegionDatabase
    from somm_simulator.models.grape import GrapeDatabase
    from somm_simulator.generators.wine_generator import generate_wine_database

    region_db = RegionDatabase()
    grape_db = GrapeDatabase()
    legacy = generate_wine_database(region_db, grape_db, target_count=target_count, seed=seed)
    return [from_legacy_wine(wine) for wine in legacy]


@dataclass(frozen=True)
class CoverageReport:
    countries: int
    major_regions: int
    subregions: int
    communes: int
    grape_varieties: int


def legacy_coverage_report() -> CoverageReport:
    from somm_simulator.models.region import RegionDatabase
    from somm_simulator.models.grape import GrapeDatabase
    region_db = RegionDatabase()
    grape_db = GrapeDatabase()
    countries = len(region_db.countries)
    major_regions = sum(len(c.wine_regions) for c in region_db.countries)
    subregions = sum(len(r.sub_regions) for c in region_db.countries for r in c.wine_regions)
    communes = len(region_db.all_communes())
    return CoverageReport(countries, major_regions, subregions, communes, len(grape_db.varieties))


class CatalogIndex:
    def __init__(self, wines: Iterable[WineRecord]):
        self.wines = list(wines)

    def search(self, *, country: str | None = None, region: str | None = None, grape: str | None = None, style: WineStyle | None = None, max_wholesale: float | None = None, min_rarity: float | None = None) -> list[WineRecord]:
        results = self.wines
        if country:
            results = [w for w in results if w.country.lower() == country.lower()]
        if region:
            results = [w for w in results if w.region.lower() == region.lower()]
        if grape:
            g = grape.lower()
            results = [w for w in results if any(g == item.lower() for item in w.grapes)]
        if style:
            results = [w for w in results if w.style == style]
        if max_wholesale is not None:
            results = [w for w in results if w.wholesale_cost <= max_wholesale]
        if min_rarity is not None:
            results = [w for w in results if w.rarity >= min_rarity]
        return results
