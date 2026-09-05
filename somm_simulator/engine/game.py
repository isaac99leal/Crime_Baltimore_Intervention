"""Main game class — unified state machine and Pygame loop."""

import pygame
from somm_simulator.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE, COLOR_BG,
)
from somm_simulator.engine.scene_manager import SceneManager
from somm_simulator.engine.save_system import SaveSystem

from somm_simulator.scenes.unified_main_menu import UnifiedMainMenuScene
from somm_simulator.scenes.new_game import NewGameScene
from somm_simulator.scenes.unified_hub import UnifiedHubScene
from somm_simulator.scenes.wine_market import WineMarketScene
from somm_simulator.scenes.cellar import CellarScene
from somm_simulator.scenes.service import ServiceScene
from somm_simulator.scenes.blind_tasting import BlindTastingScene
from somm_simulator.scenes.week_summary import WeekSummaryScene
from sommelier_v2.unified_game import UnifiedGameState
from sommelier_v2.wine_registry import SommelierWorldRegistry


class Game:
    """Top-level controller for the unified Pygame + v2 simulation."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.save_system = SaveSystem()
        self.unified_state: UnifiedGameState | None = None
        self.scene_manager = SceneManager(self)
        self._register_scenes()

    def bind_career(
        self,
        player,
        restaurant,
        *,
        saved_state: dict | None = None,
        replace_existing: bool = False,
    ) -> UnifiedGameState:
        if (
            self.unified_state is None
            or replace_existing
            or self.unified_state.player is not player
            or self.unified_state.restaurant is not restaurant
        ):
            registry = (
                None
                if self.unified_state is None or replace_existing
                else self.unified_state.wine_registry
            )
            self.unified_state = UnifiedGameState.create(
                player=player,
                restaurant=restaurant,
                wine_registry=registry,
                saved_state=saved_state,
            )
        else:
            self.unified_state.sync_from_legacy()
            if saved_state:
                self.unified_state.restore_v2(saved_state)
        return self.unified_state

    @property
    def wine_registry(self) -> SommelierWorldRegistry | None:
        return self.unified_state.wine_registry if self.unified_state else None

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()
        pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
            else:
                self.scene_manager.handle_event(event)

    def _update(self, dt: float):
        self.scene_manager.update(dt)

    def _draw(self):
        self.screen.fill(COLOR_BG)
        self.scene_manager.draw(self.screen)
        pygame.display.flip()

    def _register_scenes(self):
        sm = self.scene_manager
        sm.register("main_menu", UnifiedMainMenuScene(self))
        sm.register("new_game", NewGameScene(self))
        sm.register("hub", UnifiedHubScene(self))
        sm.register("market", WineMarketScene(self))
        sm.register("cellar", CellarScene(self))
        sm.register("service", ServiceScene(self))
        sm.register("tasting", BlindTastingScene(self))
        sm.register("week_summary", WeekSummaryScene(self))
        sm.switch_to("main_menu")

    def quit(self):
        self.running = False
