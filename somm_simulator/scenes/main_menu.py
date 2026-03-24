"""Main menu scene — title screen with New Game, Load, Quit."""

from __future__ import annotations
from typing import TYPE_CHECKING

import pygame
from somm_simulator.engine.scene_manager import Scene
from somm_simulator.ui.components import Button, draw_text, get_font
from somm_simulator.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT_BRIGHT, COLOR_TEXT_DIM,
    COLOR_ACCENT, COLOR_GOLD, FONT_SIZE_TITLE, FONT_SIZE_HEADING,
    FONT_SIZE_SMALL, COLOR_BG,
)

if TYPE_CHECKING:
    from somm_simulator.engine.game import Game


class MainMenuScene(Scene):
    """Title screen and main menu."""

    def __init__(self, game: Game):
        super().__init__(game)
        cx = SCREEN_WIDTH // 2
        self.buttons = [
            Button(cx - 120, 380, 240, 50, "New Game",
                   callback=self._new_game, font_size=FONT_SIZE_HEADING),
            Button(cx - 120, 450, 240, 50, "Load Game",
                   callback=self._load_game, font_size=FONT_SIZE_HEADING),
            Button(cx - 120, 520, 240, 50, "Quit",
                   callback=self._quit, font_size=FONT_SIZE_HEADING),
        ]
        self.title_y_offset = 0.0

    def enter(self, **kwargs):
        self.title_y_offset = 0.0
        # Check if saves exist
        saves = self.game.save_system.list_saves()
        self.buttons[1].enabled = len(saves) > 0

    def handle_event(self, event: pygame.event.Event):
        for btn in self.buttons:
            btn.handle_event(event)

    def update(self, dt: float):
        import math
        self.title_y_offset = math.sin(pygame.time.get_ticks() / 1500.0) * 4

    def draw(self, surface: pygame.Surface):
        # Title
        ty = 160 + int(self.title_y_offset)
        draw_text(surface, "SOMM SIMULATOR", SCREEN_WIDTH // 2, ty,
                  color=COLOR_GOLD, size=48, center=True)
        draw_text(surface, "The Art of Wine Service", SCREEN_WIDTH // 2, ty + 55,
                  color=COLOR_TEXT_DIM, size=FONT_SIZE_HEADING, center=True)

        # Decorative line
        lx = SCREEN_WIDTH // 2
        pygame.draw.line(surface, COLOR_ACCENT, (lx - 100, ty + 90), (lx + 100, ty + 90), 2)

        # Buttons
        for btn in self.buttons:
            btn.draw(surface)

        # Footer
        draw_text(surface, "A sommelier career simulation", SCREEN_WIDTH // 2, 620,
                  color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL, center=True)

    def _new_game(self):
        self.game.scene_manager.switch_to("new_game")

    def _load_game(self):
        saves = self.game.save_system.list_saves()
        if saves:
            # Load most recent save
            save_data = self.game.save_system.load(saves[0]["filename"])
            if save_data:
                self.game.scene_manager.switch_to("hub", save_data=save_data)

    def _quit(self):
        self.game.quit()
