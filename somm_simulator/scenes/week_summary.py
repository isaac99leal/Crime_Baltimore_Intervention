"""Week summary scene — shows events and weekly report."""

from __future__ import annotations
from typing import TYPE_CHECKING

import pygame
from somm_simulator.engine.scene_manager import Scene
from somm_simulator.ui.components import (
    Button, Panel, draw_text, draw_wrapped_text, ScrollList,
)
from somm_simulator.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_TEXT_BRIGHT,
    COLOR_ACCENT, COLOR_GOLD, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_BORDER,
    FONT_SIZE_HEADING, FONT_SIZE_BODY, FONT_SIZE_SMALL, FONT_SIZE_TINY,
)
from somm_simulator.models.player import Player
from somm_simulator.models.restaurant import Restaurant
from somm_simulator.generators.event_generator import GameEvent

if TYPE_CHECKING:
    from somm_simulator.engine.game import Game

SEVERITY_COLORS = {
    "positive": COLOR_SUCCESS,
    "neutral": COLOR_TEXT,
    "negative": COLOR_WARNING,
    "critical": COLOR_DANGER,
}


class WeekSummaryScene(Scene):
    """Show weekly events and let the player respond."""

    def __init__(self, game: Game):
        super().__init__(game)
        self.player: Player | None = None
        self.restaurant: Restaurant | None = None
        self.events: list[GameEvent] = []
        self.current_event_idx: int = 0
        self.choice_buttons: list[Button] = []
        self.phase: str = "events"  # events, summary

        self.continue_btn = Button(SCREEN_WIDTH // 2 - 80, 620, 160, 42,
                                   "Continue", callback=self._next_event)
        self.done_btn = Button(SCREEN_WIDTH // 2 - 80, 620, 160, 42,
                               "Return to Hub", callback=self._go_hub)

    def enter(self, **kwargs):
        self.player = kwargs.get("player")
        self.restaurant = kwargs.get("restaurant")
        self.events = kwargs.get("events", [])
        self.current_event_idx = 0
        self.phase = "events" if self.events else "summary"
        self._build_choices()

    def _build_choices(self):
        self.choice_buttons = []
        if self.current_event_idx >= len(self.events):
            return
        event = self.events[self.current_event_idx]
        if event.choices:
            for i, choice in enumerate(event.choices):
                btn = Button(120, 400 + i * 55, 600, 45, choice["text"],
                             callback=lambda c=choice: self._make_choice(c),
                             font_size=FONT_SIZE_SMALL)
                self.choice_buttons.append(btn)

    def _make_choice(self, choice: dict):
        """Apply the effects of a choice."""
        effect = choice.get("effect", {})
        if self.restaurant:
            if "budget" in effect:
                self.restaurant.budget += effect["budget"]
            if "reputation" in effect:
                if self.player:
                    self.player.reputation += effect.get("reputation", 0)
            if "revenue" in effect:
                self.restaurant.current_period.wine_revenue += effect["revenue"]
        if self.player:
            if "reputation_bonus" in effect:
                self.player.reputation += effect["reputation_bonus"]

        self._next_event()

    def _next_event(self):
        self.current_event_idx += 1
        if self.current_event_idx >= len(self.events):
            self.phase = "summary"
        else:
            self._build_choices()

    def handle_event(self, event: pygame.event.Event):
        if self.phase == "events":
            for btn in self.choice_buttons:
                btn.handle_event(event)
            if not self.choice_buttons:
                self.continue_btn.handle_event(event)
        elif self.phase == "summary":
            self.done_btn.handle_event(event)

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        if self.restaurant:
            draw_text(surface, f"Week {self.restaurant.game_week} Report", 30, 20,
                      color=COLOR_GOLD, size=FONT_SIZE_HEADING)

        if self.phase == "events" and self.current_event_idx < len(self.events):
            self._draw_event(surface)
        elif self.phase == "summary":
            self._draw_summary(surface)

    def _draw_event(self, surface: pygame.Surface):
        event = self.events[self.current_event_idx]
        panel = Panel(60, 70, SCREEN_WIDTH - 120, 300)
        panel.draw(surface)

        color = SEVERITY_COLORS.get(event.severity, COLOR_TEXT)
        draw_text(surface, event.title, 80, 85, color=color, size=FONT_SIZE_HEADING)
        draw_text(surface, f"[{event.category.upper()}]  {event.severity.title()}",
                  80, 118, color=COLOR_TEXT_DIM, size=FONT_SIZE_TINY)

        draw_wrapped_text(surface, event.description, 80, 150,
                          max_width=SCREEN_WIDTH - 200, color=COLOR_TEXT,
                          size=FONT_SIZE_BODY, line_spacing=6)

        draw_text(surface, f"Event {self.current_event_idx + 1}/{len(self.events)}",
                  SCREEN_WIDTH - 180, 85, color=COLOR_TEXT_DIM, size=FONT_SIZE_TINY)

        if self.choice_buttons:
            draw_text(surface, "How do you respond?", 120, 375,
                      color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_SMALL)
            for btn in self.choice_buttons:
                btn.draw(surface)
        else:
            self.continue_btn.draw(surface)

    def _draw_summary(self, surface: pygame.Surface):
        panel = Panel(60, 70, SCREEN_WIDTH - 120, 520)
        panel.draw(surface)

        draw_text(surface, "Weekly Summary", 80, 85,
                  color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_HEADING)

        y = 130
        if self.restaurant:
            r = self.restaurant
            period = r.current_period
            lines = [
                (f"Revenue: ${period.wine_revenue:,.0f}", COLOR_SUCCESS),
                (f"Wine Cost: ${period.wine_cost:,.0f}", COLOR_WARNING),
                (f"Gross Profit: ${period.gross_profit:,.0f}",
                 COLOR_SUCCESS if period.gross_profit > 0 else COLOR_DANGER),
                (f"Pour Cost: {period.pour_cost_pct:.1f}%", COLOR_TEXT),
                (f"Purchases: ${period.purchases:,.0f}", COLOR_TEXT_DIM),
                (f"Tips: ${period.tips_earned:,.0f}", COLOR_GOLD),
                ("", None),
                (f"Budget: ${r.budget:,.0f}", COLOR_TEXT_BRIGHT),
                (f"Cellar: {r.cellar_bottles_count}/{r.cellar_capacity}", COLOR_TEXT),
                (f"Wine List: {r.wine_list_size} selections", COLOR_TEXT),
            ]
            for text, color in lines:
                if not text:
                    y += 10
                    continue
                draw_text(surface, text, 80, y, color=color, size=FONT_SIZE_BODY)
                y += 28

        if self.player:
            y += 10
            draw_text(surface, "Player Stats", 80, y,
                      color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_BODY)
            y += 28
            plines = [
                (f"Reputation: {self.player.reputation}", COLOR_GOLD),
                (f"Career: {self.player.title}", COLOR_TEXT),
                (f"Services: {self.player.services_completed}", COLOR_TEXT_DIM),
                (f"Wines Tasted: {self.player.wines_tasted}", COLOR_TEXT_DIM),
            ]
            for text, color in plines:
                draw_text(surface, text, 80, y, color=color, size=FONT_SIZE_SMALL)
                y += 22

            if self.player.can_promote:
                draw_text(surface, "PROMOTION AVAILABLE!", 80, y + 10,
                          color=COLOR_SUCCESS, size=FONT_SIZE_BODY)

        # Events recap
        if self.events:
            draw_text(surface, f"Events This Week: {len(self.events)}", 600, 130,
                      color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_BODY)
            ey = 160
            for ev in self.events:
                c = SEVERITY_COLORS.get(ev.severity, COLOR_TEXT)
                draw_text(surface, f"- {ev.title}", 600, ey, color=c,
                          size=FONT_SIZE_SMALL, max_width=500)
                ey += 22

        self.done_btn.draw(surface)

    def _go_hub(self):
        # Advance financial period
        if self.restaurant:
            self.restaurant.financial_history.append(self.restaurant.current_period)
            from somm_simulator.models.restaurant import FinancialRecord
            self.restaurant.current_period = FinancialRecord(
                period=f"Week {self.restaurant.game_week}",
            )
        self.game.scene_manager.switch_to(
            "hub", player=self.player, restaurant=self.restaurant,
        )
