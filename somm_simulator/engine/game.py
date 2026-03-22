"""Main game class — state machine and game loop."""

import pygame
from somm_simulator.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE, COLOR_BG,
)
from somm_simulator.engine.scene_manager import SceneManager
from somm_simulator.engine.save_system import SaveSystem


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

    def quit(self):
        self.running = False
