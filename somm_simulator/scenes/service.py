"""Service night scene — core gameplay loop of serving guests."""

from __future__ import annotations
from typing import TYPE_CHECKING
import random

import pygame
from somm_simulator.engine.scene_manager import Scene
from somm_simulator.ui.components import (
    Button, Panel, ScrollList, draw_text, draw_wrapped_text, ProgressBar,
)
from somm_simulator.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_TEXT_BRIGHT,
    COLOR_ACCENT, COLOR_ACCENT_LIGHT, COLOR_GOLD, COLOR_SUCCESS,
    COLOR_WARNING, COLOR_DANGER, COLOR_BORDER,
    FONT_SIZE_HEADING, FONT_SIZE_BODY, FONT_SIZE_SMALL, FONT_SIZE_TINY,
)
from somm_simulator.models.wine import CellarSlot, Wine
from somm_simulator.models.guest import Guest
from somm_simulator.models.player import Player
from somm_simulator.models.restaurant import Restaurant
from somm_simulator.generators.guest_generator import generate_service_guests

if TYPE_CHECKING:
    from somm_simulator.engine.game import Game

COURSE_ORDER = ["aperitif", "appetizer", "fish", "main", "cheese", "dessert", "digestif"]
COURSE_NAMES = {
    "aperitif": "Aperitif",
    "appetizer": "Appetizer",
    "fish": "Fish Course",
    "main": "Main Course",
    "cheese": "Cheese Course",
    "dessert": "Dessert",
    "digestif": "Digestif",
}


def _match_score(wine: Wine, guest: Guest) -> float:
    """Calculate how well a wine matches guest preferences (0-1)."""
    score = 0.5  # baseline

    prefs = guest.preferences
    # Style match
    if wine.style in prefs.preferred_colors:
        score += 0.1
    # Grape match
    for g in wine.grape_names:
        if g in prefs.preferred_grapes:
            score += 0.1
            break
    # Region match
    for r in wine.region_path:
        if r in prefs.preferred_regions:
            score += 0.1
            break
    # Price comfort
    if prefs.price_floor <= wine.suggested_retail <= prefs.price_ceiling:
        score += 0.05
    elif wine.suggested_retail > prefs.price_ceiling * 1.5:
        score -= 0.15

    # Body preference
    body_diff = abs(wine.profile.body - prefs.body_preference)
    score -= body_diff * 0.05

    # Adventure bonus for unusual wines
    if prefs.adventure_level > 0.7:
        if wine.style in ("Rosé", "Sparkling", "Fortified"):
            score += 0.05
        if any(g not in ["Cabernet Sauvignon", "Merlot", "Chardonnay", "Pinot Noir"]
               for g in wine.grape_names):
            score += 0.05

    return max(0.0, min(1.0, score))


class ServiceScene(Scene):
    """Service night — interact with guests and recommend wines."""

    def __init__(self, game: Game):
        super().__init__(game)
        self.player: Player | None = None
        self.restaurant: Restaurant | None = None
        self.guests: list[Guest] = []
        self.current_guest_idx: int = 0
        self.phase: str = "intro"  # intro, serve, results
        self.service_log: list[str] = []

        self.guest_panel = Panel(30, 60, 450, 320)
        self.wine_list_scroll = ScrollList(500, 100, 480, 430, item_height=36)

        self.recommend_btn = Button(500, 545, 230, 45, "Recommend This Wine",
                                    callback=self._recommend)
        self.skip_btn = Button(750, 545, 230, 45, "Skip / No Wine",
                               callback=self._skip_course)
        self.next_guest_btn = Button(SCREEN_WIDTH // 2 - 100, 600, 200, 45,
                                     "Next Guest", callback=self._next_guest)
        self.finish_btn = Button(SCREEN_WIDTH // 2 - 100, 600, 200, 45,
                                 "Finish Service", callback=self._finish)
        self.start_btn = Button(SCREEN_WIDTH // 2 - 100, 400, 200, 50,
                                "Begin Service", callback=self._begin_service,
                                font_size=FONT_SIZE_HEADING)

        self.selected_slot: CellarSlot | None = None
        self.mood_bar = ProgressBar(50, 350, 200, 14, color=COLOR_SUCCESS)
        self.feedback_text = ""
        self.feedback_timer = 0.0

    def enter(self, **kwargs):
        self.player = kwargs.get("player")
        self.restaurant = kwargs.get("restaurant")
        self.phase = "intro"
        self.guests = []
        self.current_guest_idx = 0
        self.service_log = []
        self.feedback_text = ""

    def _begin_service(self):
        if not self.restaurant or not self.player:
            return
        self.guests = generate_service_guests(
            self.restaurant.num_tables, self.player.career_stage,
        )
        self.phase = "serve"
        self.current_guest_idx = 0
        self._setup_guest()

    def _setup_guest(self):
        """Prepare the UI for the current guest."""
        if not self.restaurant:
            return
        wine_list = self.restaurant.wine_list
        items = []
        for slot in wine_list:
            w = slot.wine
            text = f"{w.vintage} {w.full_name} ${slot.list_price:.0f} ({slot.quantity})"
            items.append({"text": text, "data": slot, "color": COLOR_TEXT})
        self.wine_list_scroll.set_items(items)
        self.selected_slot = None

    def handle_event(self, event: pygame.event.Event):
        if self.phase == "intro":
            self.start_btn.handle_event(event)
            return

        if self.phase == "serve":
            selected = self.wine_list_scroll.handle_event(event)
            if selected:
                self.selected_slot = selected["data"]
            self.recommend_btn.handle_event(event)
            self.skip_btn.handle_event(event)

        if self.phase == "between_guests":
            if self.current_guest_idx < len(self.guests) - 1:
                self.next_guest_btn.handle_event(event)
            else:
                self.finish_btn.handle_event(event)

        if self.phase == "results":
            self.finish_btn.handle_event(event)

    def update(self, dt: float):
        if self.feedback_timer > 0:
            self.feedback_timer -= dt
        self.recommend_btn.enabled = self.selected_slot is not None and self.phase == "serve"

    def draw(self, surface: pygame.Surface):
        if self.phase == "intro":
            self._draw_intro(surface)
            return
        if self.phase == "results":
            self._draw_results(surface)
            return

        # Header
        if self.guests:
            draw_text(surface, f"Service Night — Guest {self.current_guest_idx + 1}/{len(self.guests)}",
                      30, 20, color=COLOR_GOLD, size=FONT_SIZE_HEADING)

        # Guest info panel
        self.guest_panel.draw(surface)
        if self.guests and self.current_guest_idx < len(self.guests):
            g = self.guests[self.current_guest_idx]
            draw_text(surface, g.name, 50, 75, color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_BODY)
            draw_text(surface, f"Table for {g.party_size}  |  {g.archetype.title().replace('_', ' ')}",
                      50, 100, color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)

            if g.celebration:
                draw_text(surface, f"Celebrating: {g.celebration}", 50, 122,
                          color=COLOR_GOLD, size=FONT_SIZE_SMALL)
            if g.has_dietary_restriction:
                draw_text(surface, f"Dietary: {g.has_dietary_restriction}", 50, 140,
                          color=COLOR_WARNING, size=FONT_SIZE_SMALL)

            # Conversation hints
            hy = 168
            draw_text(surface, "Observations:", 50, hy, color=COLOR_TEXT_DIM, size=FONT_SIZE_TINY)
            hy += 18
            for hint in g.conversation_hints:
                draw_text(surface, f"  - {hint}", 50, hy,
                          color=COLOR_TEXT, size=FONT_SIZE_TINY, max_width=400)
                hy += 18

            # Current course
            course_name = COURSE_NAMES.get(g.current_course, g.current_course)
            draw_text(surface, f"Current Course: {course_name}", 50, 290,
                      color=COLOR_ACCENT_LIGHT, size=FONT_SIZE_BODY)

            # Mood
            draw_text(surface, f"Mood: {g.mood.title()}", 50, 318,
                      color=COLOR_TEXT, size=FONT_SIZE_SMALL)
            self.mood_bar.value = g.satisfaction
            self.mood_bar.draw(surface)

            # Spending
            draw_text(surface, f"Spent: ${g.total_spent:.0f}", 300, 350,
                      color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)

        # Wine list panel
        draw_text(surface, "Your Wine List:", 500, 75, color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_SMALL)
        self.wine_list_scroll.draw(surface)

        if self.phase == "serve":
            self.recommend_btn.draw(surface)
            self.skip_btn.draw(surface)
        elif self.phase == "between_guests":
            if self.current_guest_idx < len(self.guests) - 1:
                self.next_guest_btn.draw(surface)
            else:
                self.finish_btn.draw(surface)

        # Feedback
        if self.feedback_text and self.feedback_timer > 0:
            color = COLOR_SUCCESS if "delighted" in self.feedback_text.lower() or \
                "pleased" in self.feedback_text.lower() else COLOR_WARNING
            draw_text(surface, self.feedback_text, SCREEN_WIDTH // 2, 660,
                      color=color, size=FONT_SIZE_SMALL, center=True)

    def _draw_intro(self, surface: pygame.Surface):
        draw_text(surface, "Service Night", SCREEN_WIDTH // 2, 180,
                  color=COLOR_GOLD, size=36, center=True)
        if self.restaurant:
            draw_text(surface, self.restaurant.name, SCREEN_WIDTH // 2, 230,
                      color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_HEADING, center=True)
            draw_text(surface, f"Week {self.restaurant.game_week}", SCREEN_WIDTH // 2, 265,
                      color=COLOR_TEXT_DIM, size=FONT_SIZE_BODY, center=True)
            draw_text(surface, f"Wine List: {self.restaurant.wine_list_size} selections",
                      SCREEN_WIDTH // 2, 300, color=COLOR_TEXT_DIM,
                      size=FONT_SIZE_SMALL, center=True)
            occupancy = min(self.restaurant.num_tables, 8)
            draw_text(surface, f"Expected covers: {occupancy * 2}-{occupancy * 4}",
                      SCREEN_WIDTH // 2, 330, color=COLOR_TEXT_DIM,
                      size=FONT_SIZE_SMALL, center=True)
        self.start_btn.draw(surface)

    def _draw_results(self, surface: pygame.Surface):
        draw_text(surface, "Service Complete!", SCREEN_WIDTH // 2, 60,
                  color=COLOR_GOLD, size=FONT_SIZE_HEADING, center=True)

        y = 110
        for line in self.service_log:
            color = COLOR_TEXT
            if "Tip" in line:
                color = COLOR_GOLD
            elif "delighted" in line.lower():
                color = COLOR_SUCCESS
            elif "annoyed" in line.lower():
                color = COLOR_DANGER
            draw_text(surface, line, 80, y, color=color, size=FONT_SIZE_SMALL, max_width=1100)
            y += 22
            if y > 560:
                draw_text(surface, "...", 80, y, color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)
                break

        if self.player:
            draw_text(surface, f"Total Tips Tonight: ${self._session_tips:.0f}",
                      SCREEN_WIDTH // 2, 580, color=COLOR_GOLD,
                      size=FONT_SIZE_HEADING, center=True)

        self.finish_btn.draw(surface)

    def _recommend(self):
        if not self.selected_slot or not self.guests:
            return
        if self.current_guest_idx >= len(self.guests):
            return

        guest = self.guests[self.current_guest_idx]
        slot = self.selected_slot
        wine = slot.wine
        price = slot.list_price

        # Calculate match
        score = _match_score(wine, guest)
        # Player skill modifies score
        if self.player:
            skill_bonus = self.player.skills.service_grace * 0.1
            score = min(1.0, score + skill_bonus)

        guest.react_to_wine(score)
        guest.wines_ordered.append(wine.id)
        guest.total_spent += price

        # Sell bottle
        if self.restaurant:
            self.restaurant.sell_bottle(wine.id, price)

        # Feedback
        if score > 0.7:
            self.feedback_text = f"{guest.name} is {guest.mood}! Great pairing choice."
        elif score > 0.5:
            self.feedback_text = f"{guest.name} seems {guest.mood}. Acceptable choice."
        else:
            self.feedback_text = f"{guest.name} looks {guest.mood}. Not the best match."
        self.feedback_timer = 3.0

        # Advance course
        self._advance_course(guest)

    def _skip_course(self):
        if not self.guests or self.current_guest_idx >= len(self.guests):
            return
        guest = self.guests[self.current_guest_idx]
        self.feedback_text = f"Skipped wine for {COURSE_NAMES.get(guest.current_course, 'course')}."
        self.feedback_timer = 2.0
        self._advance_course(guest)

    def _advance_course(self, guest: Guest):
        """Move to the next course or finish this guest."""
        course_idx = COURSE_ORDER.index(guest.current_course) if guest.current_course in COURSE_ORDER else 0
        if course_idx < len(COURSE_ORDER) - 1:
            guest.current_course = COURSE_ORDER[course_idx + 1]
            guest.courses_remaining = max(0, guest.courses_remaining - 1)
        else:
            # Guest is done
            self._finish_guest(guest)

    def _finish_guest(self, guest: Guest):
        """Calculate tips and log results for a finished guest."""
        tip = guest.total_spent * guest.tip_multiplier * 0.20
        if self.player:
            self.player.total_tips += tip
            self.player.services_completed += 1
            self.player.reputation += int(guest.satisfaction * 20)
            # Skill improvements
            self.player.skills.improve("service_grace", 0.005)
            self.player.skills.improve("salesmanship", 0.003)
            if guest.is_vip:
                self.player.skills.improve("service_grace", 0.01)

        self.service_log.append(
            f"{guest.name} ({guest.archetype}) — Mood: {guest.mood}, "
            f"Spent: ${guest.total_spent:.0f}, Tip: ${tip:.0f}"
        )
        self.phase = "between_guests"

    def _next_guest(self):
        self.current_guest_idx += 1
        if self.current_guest_idx < len(self.guests):
            self.phase = "serve"
            self._setup_guest()
        else:
            self.phase = "results"

    @property
    def _session_tips(self) -> float:
        total = 0.0
        for g in self.guests:
            total += g.total_spent * g.tip_multiplier * 0.20
        return total

    def _finish(self):
        if self.restaurant:
            self.restaurant.reputation_score += sum(
                int(g.satisfaction * 10) for g in self.guests
            )
        self.game.scene_manager.switch_to(
            "hub", player=self.player, restaurant=self.restaurant,
        )
