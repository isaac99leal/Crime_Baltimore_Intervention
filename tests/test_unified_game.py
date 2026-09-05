from __future__ import annotations

import unittest
from types import SimpleNamespace

from sommelier_v2.unified_game import UnifiedGameState
from sommelier_v2.wine_registry import REGISTRY_DISPLAY_NAME, SommelierWorldRegistry


class UnifiedGameStateTests(unittest.TestCase):
    def test_shared_business_fields_sync_and_serialize(self):
        player = SimpleNamespace(title="Assistant Sommelier")
        restaurant = SimpleNamespace(
            name="Test Restaurant",
            budget=15000.0,
            game_day=1,
            game_week=1,
            cellar_capacity=200,
        )
        registry = SimpleNamespace(display_name=REGISTRY_DISPLAY_NAME)
        state = UnifiedGameState.create(
            player=player, restaurant=restaurant, wine_registry=registry
        )
        self.assertEqual(state.beverage_program.cash, 15000.0)
        restaurant.budget = 12345.0
        state.sync_from_legacy()
        self.assertEqual(state.beverage_program.cash, 12345.0)
        payload = state.to_dict()
        self.assertEqual(payload["registry_name"], REGISTRY_DISPLAY_NAME)
        self.assertEqual(payload["beverage_program"]["cash"], 12345.0)

    def test_saved_v2_business_state_restores_to_legacy_model(self):
        player = SimpleNamespace(title="Sommelier")
        restaurant = SimpleNamespace(
            name="Test Restaurant",
            budget=15000.0,
            game_day=1,
            game_week=1,
            cellar_capacity=200,
        )
        registry = SimpleNamespace(display_name=REGISTRY_DISPLAY_NAME)
        saved = {
            "beverage_program": {
                "cash": 9000,
                "day": 15,
                "week": 3,
                "cellar_capacity_bottles": 350,
            }
        }
        state = UnifiedGameState.create(
            player=player,
            restaurant=restaurant,
            wine_registry=registry,
            saved_state=saved,
        )
        self.assertEqual(state.beverage_program.cash, 9000)
        self.assertEqual(restaurant.budget, 9000)
        self.assertEqual(restaurant.game_day, 15)
        self.assertEqual(restaurant.cellar_capacity, 350)


class UnifiedRegistryTests(unittest.TestCase):
    def test_registry_replaces_raw_database_with_dual_views(self):
        registry = SommelierWorldRegistry.build(target_count=25, seed=7)
        self.assertEqual(registry.display_name, "Sommelier World Registry")
        self.assertEqual(len(registry), len(registry.legacy_wines))
        self.assertGreater(len(registry), 0)
        self.assertGreater(len(registry.v2_wines), 0)
        self.assertIs(registry[0], registry.legacy_wines[0])
        self.assertIsNotNone(registry.region_db)
        self.assertIsNotNone(registry.grape_db)


if __name__ == "__main__":
    unittest.main()
