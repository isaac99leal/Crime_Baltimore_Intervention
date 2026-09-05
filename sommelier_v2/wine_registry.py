"""Unified wine registry for the playable game.

The Pygame scenes still consume legacy ``Wine`` objects.  The same registry also
carries the v2 provenance-aware commercial records and the world knowledge
catalog, so the game has one market/catalog boundary instead of a separate
``wine_database`` and v2 sidecar.
"""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from .catalog import CatalogIndex, constrain_legacy_record, from_legacy_wine
from .domain import WineRecord
from .knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from .knowledge.regional_rules import RegionGrapeRulebook

REGISTRY_DISPLAY_NAME = "Sommelier World Registry"


@dataclass
class SommelierWorldRegistry(Sequence):
    """List-compatible market registry with legacy UI and v2 views."""

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
    ) -> "SommelierWorldRegistry":
        from somm_simulator.generators.wine_generator import generate_wine_database
        from somm_simulator.models.grape import GrapeDatabase
        from somm_simulator.models.region import RegionDatabase

        region_db = RegionDatabase()
        grape_db = GrapeDatabase()
        legacy = generate_wine_database(
            region_db, grape_db, target_count=target_count, seed=seed
        )

        knowledge = WorldWineKnowledgeCatalog()
        rulebook = RegionGrapeRulebook(catalog=knowledge)
        v2: list[WineRecord] = []
        for wine in legacy:
            record = from_legacy_wine(wine)
            if strict_origin:
                record = constrain_legacy_record(record, rulebook)
            if record is not None:
                v2.append(record)
        return cls(list(legacy), v2, knowledge, region_db=region_db, grape_db=grape_db)

    # Sequence compatibility keeps the existing Pygame market/tasting scenes
    # operational while their callers migrate from the old wine_database name.
    def __len__(self) -> int:
        return len(self.legacy_wines)

    def __getitem__(self, index):
        return self.legacy_wines[index]

    def __iter__(self) -> Iterator:
        return iter(self.legacy_wines)

    @property
    def wine_database(self) -> list:
        """Deprecated compatibility view for old scene code."""
        return self.legacy_wines

    def stats(self) -> dict[str, int]:
        return {
            "unified_registry_legacy_market_wines": len(self.legacy_wines),
            "unified_registry_v2_market_records": len(self.v2_wines),
            "unified_registry_world_grape_identities": len(self.knowledge.grapes),
        }
