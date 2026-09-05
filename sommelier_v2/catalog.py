"""Catalog entry points for Sommelier Simulator v2.

The v2 default catalog is authoritative: it is generated from reviewed strict
legal specifications and verified site-claim rules through the constrained wine
builder. The old procedural catalog remains available only through the explicitly
named ``load_legacy_catalog`` compatibility function.

Legacy records can still be useful for breadth, UI stress tests, and migration
work, but regional-style plausibility is not protected-origin certification and
legacy fictional vineyard names must not be treated as factual site claims.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Sequence

from .domain import WineRecord, WineStyle


_STYLE_MAP = {style.value.lower(): style for style in WineStyle}


def _style(value: str) -> WineStyle:
    return _STYLE_MAP.get((value or "").lower(), WineStyle.OTHER)


def load_catalog(
    *,
    as_of_year: int = 2026,
    vintages: Sequence[int] | None = None,
    include_site_claims: bool = True,
    max_sites_per_spec: int | None = None,
) -> list[WineRecord]:
    """Load the default authoritative v2 catalog.

    No legacy procedural wine generation is called by this path. Every returned
    protected-origin record has passed strict grape/origin, modeled production,
    modeled release, and any emitted named-site claim gates.
    """
    from .authoritative_catalog import load_authoritative_catalog

    return load_authoritative_catalog(
        as_of_year=as_of_year,
        vintages=vintages,
        include_site_claims=include_site_claims,
        max_sites_per_spec=max_sites_per_spec,
    )


def load_default_catalog(**kwargs) -> list[WineRecord]:
    """Compatibility-friendly alias for the authoritative v2 catalog loader."""
    return load_catalog(**kwargs)


def from_legacy_wine(wine: object) -> WineRecord:
    """Convert a legacy wine object without asserting origin validity."""
    profile = getattr(wine, "profile")
    region_path = list(getattr(wine, "region_path", []))
    grapes = tuple(getattr(g, "grape", str(g)) for g in getattr(wine, "grapes", []))
    aromas = tuple(
        list(getattr(profile, "primary_aromas", []))
        + list(getattr(profile, "secondary_aromas", []))
        + list(getattr(profile, "tertiary_aromas", []))
    )
    producer = getattr(wine, "producer_name", "") or getattr(wine, "estate_name", "")
    label = getattr(wine, "estate_name", "") or getattr(wine, "appellation", "")
    return WineRecord(
        id=str(getattr(wine, "id")),
        producer=producer,
        label=label,
        country=region_path[0] if region_path else "Unknown",
        region=(
            region_path[1]
            if len(region_path) > 1
            else (region_path[0] if region_path else "Unknown")
        ),
        subregion=region_path[2] if len(region_path) > 2 else "",
        appellation=getattr(wine, "appellation", ""),
        vineyard=getattr(wine, "vineyard_name", ""),
        vintage=int(getattr(wine, "vintage", 0)),
        style=_style(getattr(wine, "style", "")),
        grapes=grapes,
        classification=getattr(wine, "classification", ""),
        wholesale_cost=float(getattr(wine, "wholesale_cost", 0.0)),
        rarity=float(getattr(wine, "rarity", 0.0)),
        acidity=float(getattr(profile, "acidity", 3.0)),
        tannin=float(getattr(profile, "tannin", 3.0)),
        body=float(getattr(profile, "body", 3.0)),
        sweetness=float(getattr(profile, "sweetness", 1.0)),
        alcohol=float(getattr(profile, "alcohol", 13.0)),
        fruit_intensity=float(getattr(profile, "fruit_intensity", 3.0)),
        earth_intensity=float(getattr(profile, "earth_intensity", 2.0)),
        oak_influence=float(getattr(profile, "oak_influence", 2.0)),
        aromas=aromas,
        winemaking_notes=getattr(wine, "winemaking_notes", ""),
        farming_notes=getattr(wine, "farming_notes", ""),
        drink_window_start=int(getattr(wine, "drink_window_start", 0)),
        drink_window_end=int(getattr(wine, "drink_window_end", 0)),
        is_organic=bool(getattr(wine, "is_organic", False)),
        is_biodynamic=bool(getattr(wine, "is_biodynamic", False)),
        is_natural=bool(getattr(wine, "is_natural", False)),
        is_ungrafted=bool(getattr(wine, "is_ungrafted", False)),
        is_old_vine=bool(getattr(wine, "is_old_vine", False)),
    )


def legacy_record_origin_decision(record: WineRecord, rulebook: object | None = None):
    """Return the non-legal regional plausibility decision for a legacy record.

    The legacy region catalog has broad ``primary_grapes`` coverage but does not
    contain sourced exhaustive ``allowed_grapes`` legal lists. This bridge may
    therefore certify only ``regional_style`` plausibility, never protected-origin
    legality.
    """
    if rulebook is None:
        from .knowledge.regional_rules import RegionGrapeRulebook

        rulebook = RegionGrapeRulebook()
    return rulebook.evaluate(
        country=record.country,
        region=record.region,
        sub_region=record.subregion or None,
        appellation=record.appellation or None,
        grapes=record.grapes,
        label_scope="regional_style",
        vintage_year=record.vintage or 2023,
    )


def constrain_legacy_record(record: WineRecord, rulebook: object | None = None) -> WineRecord | None:
    """Canonicalize and accept only a plausible legacy origin/grape record."""
    decision = legacy_record_origin_decision(record, rulebook)
    if not decision.eligible:
        return None
    return replace(record, grapes=decision.canonical_grapes)


def load_legacy_catalog(
    target_count: int = 10_000,
    seed: int = 42,
    *,
    strict_origin: bool = True,
) -> list[WineRecord]:
    """Explicitly load non-authoritative legacy procedural breadth.

    This path is retained for migration, benchmarking, and stress testing. Even
    with ``strict_origin=True`` it performs only a non-legal regional-style guard.
    It must not be used as the authoritative v2 game catalog.
    """
    from somm_simulator.generators.wine_generator import generate_wine_database
    from somm_simulator.models.grape import GrapeDatabase
    from somm_simulator.models.region import RegionDatabase

    region_db = RegionDatabase()
    grape_db = GrapeDatabase()
    legacy = generate_wine_database(
        region_db,
        grape_db,
        target_count=target_count,
        seed=seed,
    )
    records = [from_legacy_wine(wine) for wine in legacy]
    if not strict_origin:
        return records

    from .knowledge.regional_rules import RegionGrapeRulebook

    rulebook = RegionGrapeRulebook()
    accepted: list[WineRecord] = []
    for record in records:
        constrained = constrain_legacy_record(record, rulebook)
        if constrained is not None:
            accepted.append(constrained)
    return accepted


@dataclass(frozen=True)
class CoverageReport:
    countries: int
    major_regions: int
    subregions: int
    communes: int
    grape_varieties: int


def legacy_coverage_report() -> CoverageReport:
    from somm_simulator.models.grape import GrapeDatabase
    from somm_simulator.models.region import RegionDatabase

    region_db = RegionDatabase()
    grape_db = GrapeDatabase()
    countries = len(region_db.countries)
    major_regions = sum(len(c.wine_regions) for c in region_db.countries)
    subregions = sum(
        len(r.sub_regions) for c in region_db.countries for r in c.wine_regions
    )
    communes = len(region_db.all_communes())
    return CoverageReport(
        countries,
        major_regions,
        subregions,
        communes,
        len(grape_db.varieties),
    )


class CatalogIndex:
    def __init__(self, wines: Iterable[WineRecord]):
        self.wines = list(wines)

    def search(
        self,
        *,
        country: str | None = None,
        region: str | None = None,
        grape: str | None = None,
        style: WineStyle | None = None,
        max_wholesale: float | None = None,
        min_rarity: float | None = None,
    ) -> list[WineRecord]:
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
