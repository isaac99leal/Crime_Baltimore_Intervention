"""Main game class — state machine and game loop."""

import pygame
from somm_simulator.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE, COLOR_BG,
)
from somm_simulator.engine.scene_manager import SceneManager
from somm_simulator.engine.save_system import SaveSystem

# Import all scenes
from somm_simulator.scenes.main_menu import MainMenuScene
from somm_simulator.scenes.new_game import NewGameScene
from somm_simulator.scenes.hub import HubScene
from somm_simulator.scenes.wine_market import WineMarketScene
from somm_simulator.scenes.cellar import CellarScene
from somm_simulator.scenes.service import ServiceScene
from somm_simulator.scenes.blind_tasting import BlindTastingScene
from somm_simulator.scenes.week_summary import WeekSummaryScene


class Game:
    """Top-level game controller."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.save_system = SaveSystem()
        self.scene_manager = SceneManager(self)
        self._register_scenes()

    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # Delta time in seconds
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
        """Register all game scenes."""
        sm = self.scene_manager
        sm.register("main_menu", MainMenuScene(self))
        sm.register("new_game", NewGameScene(self))
        sm.register("hub", HubScene(self))
        sm.register("market", WineMarketScene(self))
        sm.register("cellar", CellarScene(self))
        sm.register("service", ServiceScene(self))
        sm.register("tasting", BlindTastingScene(self))
        sm.register("week_summary", WeekSummaryScene(self))
        sm.switch_to("main_menu")

    def quit(self):
        self.running = False
