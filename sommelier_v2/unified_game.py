"""One root state for the playable Sommelier Simulator.

The legacy Pygame models remain the UI-facing compatibility layer.  The v2
``BeverageProgram`` is the business/simulation authority and both are bound to
one ``SommelierWorldRegistry``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import BeverageProgram
from .wine_registry import SommelierWorldRegistry


@dataclass
class UnifiedGameState:
    player: Any
    restaurant: Any
    beverage_program: BeverageProgram
    wine_registry: SommelierWorldRegistry

    @classmethod
    def create(
        cls,
        *,
        player: Any,
        restaurant: Any,
        wine_registry: SommelierWorldRegistry | None = None,
        saved_state: dict | None = None,
    ) -> "UnifiedGameState":
        registry = wine_registry or SommelierWorldRegistry.build()
        program = BeverageProgram(
            name=restaurant.name,
            cash=float(restaurant.budget),
            day=int(restaurant.game_day),
            week=int(restaurant.game_week),
            cellar_capacity_bottles=int(restaurant.cellar_capacity),
        )
        state = cls(player, restaurant, program, registry)
        state.sync_from_legacy()
        if saved_state:
            state.restore_v2(saved_state)
        return state

    def sync_from_legacy(self) -> None:
        """Copy shared business fields from the UI compatibility models."""
        self.beverage_program.name = self.restaurant.name
        self.beverage_program.cash = float(self.restaurant.budget)
        self.beverage_program.day = int(self.restaurant.game_day)
        self.beverage_program.week = int(self.restaurant.game_week)
        self.beverage_program.cellar_capacity_bottles = int(
            self.restaurant.cellar_capacity
        )
        if hasattr(self.player, "title"):
            self.beverage_program.career.title = str(self.player.title)

    def sync_to_legacy(self) -> None:
        """Apply v2 business mutations back to the current Pygame models."""
        self.restaurant.name = self.beverage_program.name
        self.restaurant.budget = float(self.beverage_program.cash)
        self.restaurant.game_day = int(self.beverage_program.day)
        self.restaurant.game_week = int(self.beverage_program.week)
        self.restaurant.cellar_capacity = int(
            self.beverage_program.cellar_capacity_bottles
        )

    def restore_v2(self, payload: dict) -> None:
        program = payload.get("beverage_program", payload)
        if "cash" in program:
            self.beverage_program.cash = float(program["cash"])
            self.restaurant.budget = self.beverage_program.cash
        if "day" in program:
            self.beverage_program.day = int(program["day"])
            self.restaurant.game_day = self.beverage_program.day
        if "week" in program:
            self.beverage_program.week = int(program["week"])
            self.restaurant.game_week = self.beverage_program.week
        if "cellar_capacity_bottles" in program:
            self.beverage_program.cellar_capacity_bottles = int(
                program["cellar_capacity_bottles"]
            )
            self.restaurant.cellar_capacity = (
                self.beverage_program.cellar_capacity_bottles
            )

    def to_dict(self) -> dict:
        self.sync_from_legacy()
        return {
            "schema": "sommelier-unified-game-v1",
            "registry_name": self.wine_registry.display_name,
            "beverage_program": {
                "name": self.beverage_program.name,
                "cash": self.beverage_program.cash,
                "day": self.beverage_program.day,
                "week": self.beverage_program.week,
                "cellar_capacity_bottles": (
                    self.beverage_program.cellar_capacity_bottles
                ),
                "time_blocks_remaining": self.beverage_program.time_blocks_remaining,
            },
        }
