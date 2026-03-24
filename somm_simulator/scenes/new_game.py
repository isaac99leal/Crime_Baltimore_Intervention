"""New game setup — character and restaurant naming."""

from __future__ import annotations
from typing import TYPE_CHECKING

import pygame
from somm_simulator.engine.scene_manager import Scene
from somm_simulator.ui.components import (
    Button, TextInput, draw_text, Panel,
)
from somm_simulator.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_TEXT_DIM,
    COLOR_TEXT_BRIGHT, COLOR_ACCENT, COLOR_GOLD, COLOR_BORDER,
    FONT_SIZE_TITLE, FONT_SIZE_HEADING, FONT_SIZE_BODY, FONT_SIZE_SMALL,
)
from somm_simulator.models.player import Player
from somm_simulator.models.restaurant import Restaurant

if TYPE_CHECKING:
    from somm_simulator.engine.game import Game


class NewGameScene(Scene):
    """Character and restaurant creation."""

    def __init__(self, game: Game):
        super().__init__(game)
        cx = SCREEN_WIDTH // 2
        self.panel = Panel(cx - 250, 120, 500, 480)

        self.name_input = TextInput(cx - 180, 260, 360, 42, placeholder="Your name...")
        self.restaurant_input = TextInput(cx - 180, 370, 360, 42, placeholder="Restaurant name...")

        self.start_btn = Button(cx - 100, 480, 200, 48, "Begin Career",
                                callback=self._start, font_size=FONT_SIZE_HEADING)
        self.back_btn = Button(cx - 100, 545, 200, 40, "Back",
                               callback=self._back, font_size=FONT_SIZE_BODY)
        self.step = 0  # 0 = name, 1 = restaurant

    def enter(self, **kwargs):
        self.name_input.text = ""
        self.restaurant_input.text = ""
        self.name_input.active = True
        self.restaurant_input.active = False

    def handle_event(self, event: pygame.event.Event):
        self.name_input.handle_event(event)
        self.restaurant_input.handle_event(event)
        self.start_btn.handle_event(event)
        self.back_btn.handle_event(event)

    def update(self, dt: float):
        self.name_input.update(dt)
        self.restaurant_input.update(dt)
        # Enable start only when both fields have text
        self.start_btn.enabled = bool(self.name_input.text.strip() and
                                       self.restaurant_input.text.strip())

    def draw(self, surface: pygame.Surface):
        self.panel.draw(surface)
        cx = SCREEN_WIDTH // 2

        draw_text(surface, "New Career", cx, 150,
                  color=COLOR_GOLD, size=FONT_SIZE_TITLE, center=True)

        # Name section
        draw_text(surface, "Your Name", cx - 180, 235,
                  color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)
        self.name_input.draw(surface)

        # Restaurant section
        draw_text(surface, "Restaurant Name", cx - 180, 345,
                  color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)
        self.restaurant_input.draw(surface)

        # Role description
        draw_text(surface, "Starting as: Assistant Sommelier", cx, 430,
                  color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL, center=True)

        self.start_btn.draw(surface)
        self.back_btn.draw(surface)

    def _start(self):
        player = Player(name=self.name_input.text.strip())
        restaurant = Restaurant(name=self.restaurant_input.text.strip())
        self.game.scene_manager.switch_to(
            "hub", player=player, restaurant=restaurant, is_new=True,
        )

    def _back(self):
        self.game.scene_manager.switch_to("main_menu")
