"""Hub adapter that binds the existing Pygame scenes to the unified v2 state."""
from __future__ import annotations

from somm_simulator.models.player import Player
from somm_simulator.models.restaurant import Restaurant
from somm_simulator.scenes.hub import HubScene
from sommelier_v2.wine_registry import REGISTRY_DISPLAY_NAME


class UnifiedHubScene(HubScene):
    """Compatibility UI over one unified game/registry state."""

    def _attach_state(self) -> None:
        if not self.player or not self.restaurant:
            return
        state = self.game.bind_career(self.player, self.restaurant)
        self.wine_database = state.wine_registry
        self.region_db = state.wine_registry.region_db
        self.grape_db = state.wine_registry.grape_db

    def _init_new_game(self):
        self._attach_state()
        self.notification = (
            f"{REGISTRY_DISPLAY_NAME}: {len(self.wine_database):,} market wines; "
            f"{len(self.game.unified_state.wine_registry.v2_wines):,} v2 records."
        )
        self.notification_timer = 5.0

    def _load_from_save(self, save_data: dict):
        # Accept the old wrapper and the corrected direct state shape.
        state = save_data.get("game_state", save_data)
        self.player = Player.from_dict(state["player"])
        r_data = state.get("restaurant", {})
        self.restaurant = Restaurant(
            name=r_data.get("name", "Le Ciel Étoilé"),
            budget=r_data.get("budget", 15000),
            cellar_capacity=r_data.get("cellar_capacity", 200),
            num_tables=r_data.get("num_tables", 8),
            game_day=r_data.get("game_day", 1),
            game_week=r_data.get("game_week", 1),
            storage_temp_f=r_data.get("storage_temp_f", 55.0),
            storage_humidity=r_data.get("storage_humidity", 70.0),
            reputation_score=r_data.get("reputation_score", 0),
        )
        unified_saved = state.get("unified_state")
        unified = self.game.bind_career(
            self.player,
            self.restaurant,
            saved_state=unified_saved,
            replace_existing=True,
        )
        self.wine_database = unified.wine_registry
        self.region_db = unified.wine_registry.region_db
        self.grape_db = unified.wine_registry.grape_db
        self.notification = f"Loaded with {unified.wine_registry.display_name}."
        self.notification_timer = 4.0

    def enter(self, **kwargs):
        super().enter(**kwargs)
        if self.game.unified_state is not None:
            self.game.unified_state.sync_from_legacy()
            self.wine_database = self.game.unified_state.wine_registry
            self.region_db = self.game.unified_state.wine_registry.region_db
            self.grape_db = self.game.unified_state.wine_registry.grape_db

    def _advance_week(self):
        super()._advance_week()
        if self.game.unified_state is not None:
            self.game.unified_state.sync_from_legacy()

    def _save_game(self):
        if not self.player or not self.restaurant:
            return
        unified = self.game.bind_career(self.player, self.restaurant)
        state = {
            "player": self.player.to_dict(),
            "restaurant": self.restaurant.to_dict(),
            "unified_state": unified.to_dict(),
        }
        self.game.save_system.save(self.player.name, state)
        self.notification = "Game saved."
        self.notification_timer = 3.0
