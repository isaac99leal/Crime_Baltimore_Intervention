"""Wine market scene — browse and purchase wines."""

from __future__ import annotations
from typing import TYPE_CHECKING
import random

import pygame
from somm_simulator.engine.scene_manager import Scene
from somm_simulator.ui.components import (
    Button, Panel, ScrollList, TabBar, draw_text, draw_wrapped_text,
)
from somm_simulator.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_TEXT_BRIGHT,
    COLOR_ACCENT, COLOR_GOLD, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_BORDER, COLOR_BG_PANEL, WINE_COLOR_RED, WINE_COLOR_WHITE,
    WINE_COLOR_ROSE, WINE_COLOR_SPARKLING,
    FONT_SIZE_HEADING, FONT_SIZE_BODY, FONT_SIZE_SMALL, FONT_SIZE_TINY,
)
from somm_simulator.models.wine import Wine, CellarSlot
from somm_simulator.models.player import Player
from somm_simulator.models.restaurant import Restaurant

if TYPE_CHECKING:
    from somm_simulator.engine.game import Game

STYLE_COLORS = {
    "Red": WINE_COLOR_RED,
    "White": WINE_COLOR_WHITE,
    "Rosé": WINE_COLOR_ROSE,
    "Sparkling": WINE_COLOR_SPARKLING,
}


class WineMarketScene(Scene):
    """Browse and buy wines from the market."""

    def __init__(self, game: Game):
        super().__init__(game)
        self.player: Player | None = None
        self.restaurant: Restaurant | None = None
        self.all_wines: list[Wine] = []
        self.filtered_wines: list[Wine] = []
        self.selected_wine: Wine | None = None

        # Market offers a random subset each visit
        self.market_wines: list[Wine] = []

        self.wine_list = ScrollList(30, 100, 500, 530, item_height=40)
        self.tabs = TabBar(30, 60, 500, ["All", "Red", "White", "Sparkling", "Value", "Premium"])

        self.buy_1_btn = Button(560, 520, 160, 42, "Buy 1 Bottle",
                                callback=lambda: self._buy(1))
        self.buy_6_btn = Button(560, 572, 160, 42, "Buy 6 (Case)",
                                callback=lambda: self._buy(6))
        self.buy_12_btn = Button(740, 520, 160, 42, "Buy 12 (Case)",
                                 callback=lambda: self._buy(12))
        self.back_btn = Button(SCREEN_WIDTH - 120, 20, 100, 36, "Back",
                               callback=self._go_back, font_size=FONT_SIZE_SMALL)
        self.refresh_btn = Button(560, 625, 160, 36, "New Offerings",
                                  callback=self._refresh_market, font_size=FONT_SIZE_SMALL)

        self.message = ""
        self.message_timer = 0.0

    def enter(self, **kwargs):
        self.player = kwargs.get("player")
        self.restaurant = kwargs.get("restaurant")
        self.all_wines = kwargs.get("wine_database", [])
        self._refresh_market()

    def _refresh_market(self):
        """Generate a fresh subset of available wines."""
        n = min(120, len(self.all_wines))
        self.market_wines = random.sample(self.all_wines, n) if self.all_wines else []
        self._apply_filter(0)
        self.selected_wine = None

    def _apply_filter(self, tab_idx: int):
        if tab_idx == 0:
            self.filtered_wines = self.market_wines
        elif tab_idx == 1:
            self.filtered_wines = [w for w in self.market_wines if w.style == "Red"]
        elif tab_idx == 2:
            self.filtered_wines = [w for w in self.market_wines if w.style == "White"]
        elif tab_idx == 3:
            self.filtered_wines = [w for w in self.market_wines
                                   if w.style in ("Sparkling", "Rosé")]
        elif tab_idx == 4:  # Value
            self.filtered_wines = sorted(
                [w for w in self.market_wines if w.wholesale_cost < 30],
                key=lambda w: w.wholesale_cost)
        elif tab_idx == 5:  # Premium
            self.filtered_wines = sorted(
                [w for w in self.market_wines if w.wholesale_cost >= 30],
                key=lambda w: -w.wholesale_cost)

        items = []
        for w in self.filtered_wines:
            sc = STYLE_COLORS.get(w.style, COLOR_TEXT)
            text = f"{w.vintage} {w.full_name} — ${w.wholesale_cost:.0f}"
            items.append({"text": text, "data": w, "color": sc})
        self.wine_list.set_items(items)

    def handle_event(self, event: pygame.event.Event):
        tab = self.tabs.handle_event(event)
        if tab is not None:
            self._apply_filter(tab)

        selected = self.wine_list.handle_event(event)
        if selected:
            self.selected_wine = selected["data"]

        self.buy_1_btn.handle_event(event)
        self.buy_6_btn.handle_event(event)
        self.buy_12_btn.handle_event(event)
        self.back_btn.handle_event(event)
        self.refresh_btn.handle_event(event)

    def update(self, dt: float):
        if self.message_timer > 0:
            self.message_timer -= dt
        can_buy = self.selected_wine is not None and self.restaurant is not None
        self.buy_1_btn.enabled = can_buy
        self.buy_6_btn.enabled = can_buy
        self.buy_12_btn.enabled = can_buy

    def draw(self, surface: pygame.Surface):
        draw_text(surface, "Wine Market", 30, 20,
                  color=COLOR_GOLD, size=FONT_SIZE_HEADING)

        if self.restaurant:
            draw_text(surface, f"Budget: ${self.restaurant.budget:,.0f}",
                      300, 25, color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)
            draw_text(surface, f"Cellar Space: {self.restaurant.cellar_space_remaining}",
                      500, 25, color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)

        self.back_btn.draw(surface)
        self.tabs.draw(surface)
        self.wine_list.draw(surface)

        # Wine detail panel
        detail_panel = Panel(550, 60, 480, 445)
        detail_panel.draw(surface)

        if self.selected_wine:
            w = self.selected_wine
            dy = 75
            draw_text(surface, w.full_name, 570, dy,
                      color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_HEADING)
            dy += 30

            details = [
                (f"Vintage: {w.vintage}", COLOR_TEXT),
                (f"Style: {w.style}", STYLE_COLORS.get(w.style, COLOR_TEXT)),
                (f"Region: {' > '.join(w.region_path)}", COLOR_TEXT_DIM),
                (f"Grapes: {', '.join(w.grape_names)}", COLOR_TEXT),
                (f"Classification: {w.classification}", COLOR_GOLD),
                (f"Condition: {w.current_condition}", COLOR_TEXT),
                (f"Alcohol: {w.profile.alcohol}%", COLOR_TEXT_DIM),
                ("", COLOR_TEXT),
                (f"Wholesale: ${w.wholesale_cost:.2f}/bottle", COLOR_WARNING),
                (f"Suggested Retail: ${w.suggested_retail:.2f}", COLOR_TEXT_DIM),
                (f"Available: {w.quantity_available} bottles", COLOR_TEXT_DIM),
                ("", COLOR_TEXT),
                (f"Aging Potential: {w.aging_potential_years} years", COLOR_TEXT),
                (f"Drink Window: {w.vintage + w.drink_window_start}–{w.vintage + w.drink_window_end}", COLOR_TEXT_DIM),
            ]
            if w.special_designation:
                details.append((f"Designation: {w.special_designation}", COLOR_GOLD))
            if w.winemaking_notes:
                details.append((f"Notes: {w.winemaking_notes}", COLOR_TEXT_DIM))

            # Tasting profile
            p = w.profile
            details.append(("", COLOR_TEXT))
            details.append(("--- Tasting Profile ---", COLOR_ACCENT))
            details.append((f"Acidity: {'*' * int(p.acidity)}  Body: {'*' * int(p.body)}  Tannin: {'*' * int(p.tannin)}", COLOR_TEXT_DIM))
            if p.primary_aromas:
                details.append((f"Aromas: {', '.join(p.primary_aromas[:4])}", COLOR_TEXT_DIM))

            for text, color in details:
                if not text:
                    dy += 6
                    continue
                draw_text(surface, text, 570, dy,
                          color=color, size=FONT_SIZE_TINY, max_width=440)
                dy += 18
        else:
            draw_text(surface, "Select a wine to view details", 640, 280,
                      color=COLOR_TEXT_DIM, size=FONT_SIZE_BODY, center=True)

        # Buy buttons
        self.buy_1_btn.draw(surface)
        self.buy_6_btn.draw(surface)
        self.buy_12_btn.draw(surface)
        self.refresh_btn.draw(surface)

        # Message
        if self.message and self.message_timer > 0:
            color = COLOR_SUCCESS if "Purchased" in self.message else COLOR_DANGER
            draw_text(surface, self.message, 640, 670,
                      color=color, size=FONT_SIZE_SMALL, center=True)

    def _buy(self, qty: int):
        if not self.selected_wine or not self.restaurant:
            return
        w = self.selected_wine
        total_cost = w.wholesale_cost * qty
        if total_cost > self.restaurant.budget:
            self.message = f"Not enough budget! Need ${total_cost:.0f}"
            self.message_timer = 3.0
            return
        if qty > self.restaurant.cellar_space_remaining:
            self.message = f"Not enough cellar space! Need {qty} slots"
            self.message_timer = 3.0
            return
        if qty > w.quantity_available:
            self.message = f"Only {w.quantity_available} bottles available"
            self.message_timer = 3.0
            return

        # Purchase
        slot = CellarSlot(
            wine=w,
            quantity=qty,
            purchase_price=w.wholesale_cost,
            date_acquired=self.restaurant.game_day,
        )
        self.restaurant.add_to_cellar(slot)
        self.restaurant.budget -= total_cost
        self.restaurant.current_period.purchases += total_cost
        w.quantity_available -= qty

        self.message = f"Purchased {qty}x {w.full_name} for ${total_cost:.0f}"
        self.message_timer = 4.0

    def _go_back(self):
        self.game.scene_manager.switch_to(
            "hub", player=self.player, restaurant=self.restaurant,
        )
