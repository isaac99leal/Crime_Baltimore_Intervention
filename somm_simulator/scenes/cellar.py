"""Cellar management scene — view inventory, manage wine list."""

from __future__ import annotations
from typing import TYPE_CHECKING

import pygame
from somm_simulator.engine.scene_manager import Scene
from somm_simulator.ui.components import (
    Button, Panel, ScrollList, TabBar, draw_text,
)
from somm_simulator.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_TEXT_BRIGHT,
    COLOR_ACCENT, COLOR_GOLD, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_BORDER, WINE_COLOR_RED, WINE_COLOR_WHITE,
    FONT_SIZE_HEADING, FONT_SIZE_BODY, FONT_SIZE_SMALL, FONT_SIZE_TINY,
    BASE_WINE_MARKUP,
)
from somm_simulator.models.wine import CellarSlot
from somm_simulator.models.player import Player
from somm_simulator.models.restaurant import Restaurant

if TYPE_CHECKING:
    from somm_simulator.engine.game import Game


class CellarScene(Scene):
    """View and manage wine cellar and wine list."""

    def __init__(self, game: Game):
        super().__init__(game)
        self.player: Player | None = None
        self.restaurant: Restaurant | None = None
        self.selected_slot: CellarSlot | None = None

        self.wine_list_view = ScrollList(30, 100, 480, 530, item_height=40)
        self.tabs = TabBar(30, 60, 480, ["All Cellar", "On Wine List", "Not Listed"])

        self.toggle_btn = Button(540, 520, 200, 42, "Add to Wine List",
                                 callback=self._toggle_list)
        self.price_up_btn = Button(540, 572, 95, 36, "Price +10%",
                                   callback=self._price_up, font_size=FONT_SIZE_SMALL)
        self.price_down_btn = Button(645, 572, 95, 36, "Price -10%",
                                     callback=self._price_down, font_size=FONT_SIZE_SMALL)
        self.auto_price_btn = Button(540, 616, 200, 36, "Auto-Price (3x Cost)",
                                     callback=self._auto_price, font_size=FONT_SIZE_SMALL)
        self.back_btn = Button(SCREEN_WIDTH - 120, 20, 100, 36, "Back",
                               callback=self._go_back, font_size=FONT_SIZE_SMALL)

        self.message = ""
        self.message_timer = 0.0

    def enter(self, **kwargs):
        self.player = kwargs.get("player")
        self.restaurant = kwargs.get("restaurant")
        self._refresh_list(0)

    def _refresh_list(self, tab_idx: int):
        if not self.restaurant:
            return
        cellar = self.restaurant.cellar
        if tab_idx == 1:
            slots = [s for s in cellar if s.on_wine_list]
        elif tab_idx == 2:
            slots = [s for s in cellar if not s.on_wine_list]
        else:
            slots = cellar

        items = []
        for s in slots:
            w = s.wine
            status = "[LISTED]" if s.on_wine_list else ""
            price_str = f"${s.list_price:.0f}" if s.on_wine_list else ""
            color = COLOR_SUCCESS if s.on_wine_list else COLOR_TEXT
            text = f"{w.vintage} {w.full_name} x{s.quantity} {status} {price_str}"
            items.append({"text": text, "data": s, "color": color})
        self.wine_list_view.set_items(items)

    def handle_event(self, event: pygame.event.Event):
        tab = self.tabs.handle_event(event)
        if tab is not None:
            self._refresh_list(tab)

        selected = self.wine_list_view.handle_event(event)
        if selected:
            self.selected_slot = selected["data"]
            self._update_toggle_text()

        self.toggle_btn.handle_event(event)
        self.price_up_btn.handle_event(event)
        self.price_down_btn.handle_event(event)
        self.auto_price_btn.handle_event(event)
        self.back_btn.handle_event(event)

    def _update_toggle_text(self):
        if self.selected_slot and self.selected_slot.on_wine_list:
            self.toggle_btn.text = "Remove from List"
        else:
            self.toggle_btn.text = "Add to Wine List"

    def update(self, dt: float):
        if self.message_timer > 0:
            self.message_timer -= dt
        self.toggle_btn.enabled = self.selected_slot is not None
        self.price_up_btn.enabled = (self.selected_slot is not None and
                                      self.selected_slot.on_wine_list)
        self.price_down_btn.enabled = self.price_up_btn.enabled
        self.auto_price_btn.enabled = self.selected_slot is not None

    def draw(self, surface: pygame.Surface):
        draw_text(surface, "Cellar & Wine List", 30, 20,
                  color=COLOR_GOLD, size=FONT_SIZE_HEADING)

        if self.restaurant:
            draw_text(surface, f"{self.restaurant.cellar_bottles_count}/{self.restaurant.cellar_capacity} bottles",
                      350, 25, color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)
            draw_text(surface, f"Wine List: {self.restaurant.wine_list_size} selections",
                      550, 25, color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)

        self.back_btn.draw(surface)
        self.tabs.draw(surface)
        self.wine_list_view.draw(surface)

        # Detail panel
        detail_panel = Panel(530, 60, 490, 445)
        detail_panel.draw(surface)

        if self.selected_slot:
            s = self.selected_slot
            w = s.wine
            dy = 75
            draw_text(surface, w.full_name, 550, dy,
                      color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_HEADING)
            dy += 30
            info = [
                (f"Vintage: {w.vintage}  |  Style: {w.style}", COLOR_TEXT),
                (f"Region: {' > '.join(w.region_path)}", COLOR_TEXT_DIM),
                (f"Grapes: {', '.join(w.grape_names)}", COLOR_TEXT),
                (f"Classification: {w.classification}", COLOR_GOLD),
                (f"Condition: {w.current_condition}", COLOR_TEXT),
                ("", None),
                (f"Quantity in Cellar: {s.quantity} bottles", COLOR_TEXT_BRIGHT),
                (f"Purchase Price: ${s.purchase_price:.2f}/bottle", COLOR_TEXT),
                (f"Total Investment: ${s.total_value:.2f}", COLOR_WARNING),
                ("", None),
            ]
            if s.on_wine_list:
                info.append((f"List Price: ${s.list_price:.2f}", COLOR_SUCCESS))
                margin = s.list_price - s.purchase_price
                margin_pct = (margin / s.purchase_price * 100) if s.purchase_price > 0 else 0
                info.append((f"Margin: ${margin:.2f} ({margin_pct:.0f}%)", COLOR_GOLD))
                info.append((f"Potential Revenue: ${s.potential_revenue:.2f}", COLOR_TEXT_DIM))
            else:
                info.append(("Not on wine list", COLOR_TEXT_DIM))

            # Tasting profile
            p = w.profile
            info.append(("", None))
            info.append(("--- Tasting Profile ---", COLOR_ACCENT))
            info.append((f"Acidity: {'*' * int(p.acidity)}  Body: {'*' * int(p.body)}  Tannin: {'*' * int(p.tannin)}", COLOR_TEXT_DIM))
            if p.primary_aromas:
                info.append((f"Aromas: {', '.join(p.primary_aromas[:4])}", COLOR_TEXT_DIM))

            for text, color in info:
                if not text:
                    dy += 6
                    continue
                draw_text(surface, text, 550, dy,
                          color=color, size=FONT_SIZE_TINY, max_width=460)
                dy += 18
        else:
            draw_text(surface, "Select a wine to manage", 700, 280,
                      color=COLOR_TEXT_DIM, size=FONT_SIZE_BODY, center=True)

        self.toggle_btn.draw(surface)
        self.price_up_btn.draw(surface)
        self.price_down_btn.draw(surface)
        self.auto_price_btn.draw(surface)

        if self.message and self.message_timer > 0:
            draw_text(surface, self.message, 640, 670,
                      color=COLOR_SUCCESS, size=FONT_SIZE_SMALL, center=True)

    def _toggle_list(self):
        if not self.selected_slot:
            return
        s = self.selected_slot
        if s.on_wine_list:
            s.on_wine_list = False
            s.list_price = 0.0
            self.message = f"Removed {s.wine.full_name} from wine list"
        else:
            s.on_wine_list = True
            if s.list_price == 0:
                s.list_price = round(s.purchase_price * BASE_WINE_MARKUP, 2)
            self.message = f"Added {s.wine.full_name} to wine list at ${s.list_price:.0f}"
        self._update_toggle_text()
        self._refresh_list(self.tabs.active_tab)
        self.message_timer = 3.0

    def _price_up(self):
        if self.selected_slot and self.selected_slot.on_wine_list:
            self.selected_slot.list_price = round(self.selected_slot.list_price * 1.1, 2)
            self._refresh_list(self.tabs.active_tab)

    def _price_down(self):
        if self.selected_slot and self.selected_slot.on_wine_list:
            self.selected_slot.list_price = max(
                self.selected_slot.purchase_price,
                round(self.selected_slot.list_price * 0.9, 2),
            )
            self._refresh_list(self.tabs.active_tab)

    def _auto_price(self):
        if self.selected_slot:
            self.selected_slot.list_price = round(
                self.selected_slot.purchase_price * BASE_WINE_MARKUP, 2)
            if not self.selected_slot.on_wine_list:
                self.selected_slot.on_wine_list = True
            self._update_toggle_text()
            self._refresh_list(self.tabs.active_tab)
            self.message = f"Auto-priced at ${self.selected_slot.list_price:.0f}"
            self.message_timer = 3.0

    def _go_back(self):
        self.game.scene_manager.switch_to(
            "hub", player=self.player, restaurant=self.restaurant,
        )
