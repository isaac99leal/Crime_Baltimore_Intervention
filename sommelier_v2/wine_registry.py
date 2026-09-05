"""Unified wine registry for the playable game.

The v2 market is authoritative. It is generated from reviewed legal wine
specifications through ``AuthoritativeCatalogGenerator``. The current Pygame
scenes still consume legacy ``Wine`` objects, so this module creates a legacy
compatibility view of each authoritative catalog item. It does not create a
second procedural wine market.
"""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from math import ceil

from .authoritative_catalog import (
    AuthoritativeCatalogGenerator,
    AuthoritativeCatalogItem,
    LEGAL_SNAPSHOT_AS_OF_YEAR,
)
from .catalog import CatalogIndex
from .domain import WineRecord, WineStyle
from .knowledge.expanded_catalog import WorldWineKnowledgeCatalog

REGISTRY_DISPLAY_NAME = "Sommelier World Registry"


def _legacy_color(style: WineStyle) -> str:
    return {
        WineStyle.RED: "medium ruby",
        WineStyle.WHITE: "pale gold",
        WineStyle.ROSE: "pale pink",
        WineStyle.SPARKLING: "pale gold",
        WineStyle.DESSERT: "deep gold",
        WineStyle.FORTIFIED: "deep ruby",
        WineStyle.ORANGE: "amber",
    }.get(style, "medium ruby")


def _compatibility_aging(record: WineRecord) -> tuple[int, int, int]:
    """Return game-only drink-window priors for the temporary legacy UI view."""
    base = {
        WineStyle.RED: 12,
        WineStyle.WHITE: 8,
        WineStyle.ROSE: 4,
        WineStyle.SPARKLING: 10,
        WineStyle.DESSERT: 14,
        WineStyle.FORTIFIED: 18,
        WineStyle.ORANGE: 7,
    }.get(record.style, 7)
    aging = max(2, int(round(base + 10.0 * record.rarity)))
    drink_start = record.drink_window_start or max(1, aging // 4)
    drink_end = record.drink_window_end or aging
    return aging, drink_start, drink_end


def _compatibility_condition(
    *,
    vintage: int,
    as_of_year: int,
    drink_start: int,
    drink_end: int,
) -> str:
    age = max(0, as_of_year - vintage)
    if age < drink_start:
        return "Young" if age < max(1, drink_start // 2) else "Developing"
    if age <= drink_end:
        midpoint = (drink_start + drink_end) / 2.0
        return "Approaching Peak" if age < midpoint else "Peak"
    return "Past Peak" if age - drink_end < 5 else "Declining"


def authoritative_item_to_legacy_wine(
    item: AuthoritativeCatalogItem,
    *,
    as_of_year: int = LEGAL_SNAPSHOT_AS_OF_YEAR,
):
    """Create a Pygame-compatible ``Wine`` view of one authoritative record.

    Origin, vintage, grapes, blend percentages, site claim, classification, and
    legal winemaking notes come from the authoritative item. Retail multiplier,
    market quantity, drink window, and condition are deterministic compatibility
    priors used only by the old UI model.
    """
    from somm_simulator.models.wine import GrapeBlend, TastingProfile, Wine

    record = item.wine
    region_path: list[str] = [record.country]
    for value in (record.region, record.subregion, record.appellation):
        if value and all(value.casefold() != existing.casefold() for existing in region_path):
            region_path.append(value)

    profile = TastingProfile(
        acidity=record.acidity,
        tannin=record.tannin,
        body=record.body,
        sweetness=record.sweetness,
        alcohol=record.alcohol,
        fruit_intensity=record.fruit_intensity,
        earth_intensity=record.earth_intensity,
        oak_influence=record.oak_influence,
        primary_aromas=list(record.aromas[:6]),
        secondary_aromas=[],
        tertiary_aromas=[],
        color=_legacy_color(record.style),
    )

    # The legal specification may use a jurisdictional synonym (for example,
    # Pinot Nero) while the world catalog canonicalizes the identity (Pinot Noir).
    # Keep the exact legal percentages but expose the same canonical identities in
    # both object models.
    legal_percentages = [float(pct) for _, pct in item.blend_percentages]
    if len(record.grapes) == len(legal_percentages):
        grapes = [
            GrapeBlend(grape=name, percentage=pct)
            for name, pct in zip(record.grapes, legal_percentages)
        ]
    else:
        grapes = [
            GrapeBlend(grape=name, percentage=float(pct))
            for name, pct in item.blend_percentages
        ]

    estate_name = record.label
    if record.vineyard:
        suffix = f" · {record.vineyard}"
        if estate_name.endswith(suffix):
            estate_name = estate_name[: -len(suffix)]

    aging, drink_start, drink_end = _compatibility_aging(record)
    condition = _compatibility_condition(
        vintage=record.vintage,
        as_of_year=as_of_year,
        drink_start=drink_start,
        drink_end=drink_end,
    )
    quantity = max(1, int(round(120.0 * max(0.04, 1.0 - record.rarity))))
    suggested_retail = round(max(1.0, record.wholesale_cost) * 3.0, 2)
    special_designation = (
        record.classification
        if record.classification and record.classification.casefold() != "standard"
        else ""
    )

    return Wine(
        id=record.id,
        producer_name=record.producer,
        estate_name=estate_name,
        region_path=region_path,
        appellation=record.appellation,
        classification=record.classification,
        grapes=grapes,
        vintage=record.vintage,
        style=record.style.value,
        profile=profile,
        aging_potential_years=aging,
        current_condition=condition,
        wholesale_cost=record.wholesale_cost,
        suggested_retail=suggested_retail,
        rarity=record.rarity,
        quantity_available=quantity,
        vineyard_name=record.vineyard,
        special_designation=special_designation,
        winemaking_notes=record.winemaking_notes,
        drink_window_start=drink_start,
        drink_window_end=drink_end,
        is_organic=record.is_organic,
        is_biodynamic=record.is_biodynamic,
        is_natural=record.is_natural,
        is_ungrafted=record.is_ungrafted,
        is_orange_wine=record.style == WineStyle.ORANGE,
        is_old_vine=record.is_old_vine,
        farming_notes=record.farming_notes,
    )


@dataclass
class SommelierWorldRegistry(Sequence):
    """One authoritative market with legacy and v2 object views."""

    legacy_wines: list
    v2_wines: list[WineRecord]
    knowledge: WorldWineKnowledgeCatalog
    region_db: object | None = None
    grape_db: object | None = None
    display_name: str = REGISTRY_DISPLAY_NAME

    def __post_init__(self) -> None:
        self.catalog_index = CatalogIndex(self.v2_wines)

    @classmethod
    def build(
        cls,
        *,
        target_count: int = 2_000,
        seed: int = 42,
        strict_origin: bool = True,
        as_of_year: int = LEGAL_SNAPSHOT_AS_OF_YEAR,
        include_site_claims: bool = True,
    ) -> "SommelierWorldRegistry":
        """Build one legally constrained market and two object-model views.

        ``seed`` and ``strict_origin`` remain in the signature for old callers.
        Generation is deterministic and strict origin validation cannot be turned
        off on the default registry path. Use ``load_legacy_catalog`` explicitly
        for legacy procedural test data.
        """
        del seed, strict_origin
        if target_count <= 0:
            raise ValueError("target_count must be positive")

        # Legacy hierarchy/database helpers remain available because existing UI
        # code still queries them. They are no longer used to generate market wines.
        from somm_simulator.models.grape import GrapeDatabase
        from somm_simulator.models.region import RegionDatabase

        region_db = RegionDatabase()
        grape_db = GrapeDatabase()
        knowledge = WorldWineKnowledgeCatalog()
        generator = AuthoritativeCatalogGenerator(catalog=knowledge)

        # Use the maximum modeled release delay to choose a vintage that is safe
        # for every current strict specification. Add older vintages until the
        # requested market depth is reached. Every item is still independently
        # revalidated by the constrained builder.
        max_delay = max(
            (
                max(
                    1,
                    ceil((spec.min_total_aging_months or 0) / 12.0),
                    spec.release_year_offset or 0,
                )
                for spec in generator.legal_specs.specs
            ),
            default=1,
        )
        latest_common_vintage = as_of_year - max_delay
        first_pass = generator.generate(
            as_of_year=as_of_year,
            vintages=(latest_common_vintage,),
            include_site_claims=include_site_claims,
        )
        if not first_pass:
            raise RuntimeError("Authoritative catalog generation returned no market records")

        depth = max(1, ceil(target_count / len(first_pass)))
        vintages = tuple(latest_common_vintage - offset for offset in range(depth))
        items = generator.generate(
            as_of_year=as_of_year,
            vintages=vintages,
            include_site_claims=include_site_claims,
        )[:target_count]

        v2 = [item.wine for item in items]
        legacy = [
            authoritative_item_to_legacy_wine(item, as_of_year=as_of_year)
            for item in items
        ]
        return cls(
            legacy,
            v2,
            knowledge,
            region_db=region_db,
            grape_db=grape_db,
        )

    # Sequence compatibility keeps the existing Pygame market/tasting scenes
    # operational while they migrate from ``Wine`` to ``WineRecord``. These are
    # views of the authoritative records, not independently generated wines.
    def __len__(self) -> int:
        return len(self.legacy_wines)

    def __getitem__(self, index):
        return self.legacy_wines[index]

    def __iter__(self) -> Iterator:
        return iter(self.legacy_wines)

    @property
    def wine_database(self) -> list:
        """Deprecated Pygame compatibility view of the authoritative market."""
        return self.legacy_wines

    def stats(self) -> dict[str, int]:
        return {
            "unified_registry_authoritative_market_records": len(self.v2_wines),
            "unified_registry_legacy_compatibility_views": len(self.legacy_wines),
            # Historical keys remain for consumers that already display them.
            "unified_registry_legacy_market_wines": len(self.legacy_wines),
            "unified_registry_v2_market_records": len(self.v2_wines),
            "unified_registry_world_grape_identities": len(self.knowledge.grapes),
        }
