"""Blind tasting mini-game — identify wines by their tasting profile."""

from __future__ import annotations
from typing import TYPE_CHECKING
import random

import pygame
from somm_simulator.engine.scene_manager import Scene
from somm_simulator.ui.components import (
    Button, Panel, draw_text, ProgressBar,
)
from somm_simulator.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_TEXT_BRIGHT,
    COLOR_ACCENT, COLOR_ACCENT_LIGHT, COLOR_GOLD, COLOR_SUCCESS,
    COLOR_WARNING, COLOR_DANGER, COLOR_BORDER,
    FONT_SIZE_HEADING, FONT_SIZE_BODY, FONT_SIZE_SMALL, FONT_SIZE_TINY,
)
from somm_simulator.models.wine import Wine
from somm_simulator.models.player import Player
from somm_simulator.models.restaurant import Restaurant

if TYPE_CHECKING:
    from somm_simulator.engine.game import Game

# Aspects the player guesses
GUESS_CATEGORIES = ["grape", "region", "vintage_range", "style"]


class BlindTastingScene(Scene):
    """Blind tasting practice — identify wine attributes."""

    def __init__(self, game: Game):
        super().__init__(game)
        self.player: Player | None = None
        self.restaurant: Restaurant | None = None
        self.wine_database: list[Wine] = []

        self.target_wine: Wine | None = None
        self.options: dict[str, list[str]] = {}
        self.correct: dict[str, str] = {}
        self.guesses: dict[str, str | None] = {}
        self.phase: str = "tasting"  # tasting, reveal
        self.current_category: int = 0
        self.score: int = 0
        self.rounds_played: int = 0
        self.total_score: int = 0

        self.option_buttons: list[Button] = []
        self.next_btn = Button(SCREEN_WIDTH // 2 - 80, 620, 160, 42,
                               "Next Wine", callback=self._next_round)
        self.back_btn = Button(SCREEN_WIDTH - 120, 20, 100, 36, "Finish",
                               callback=self._go_back, font_size=FONT_SIZE_SMALL)

        # Profile bars
        self.profile_bars: dict[str, ProgressBar] = {}

    def enter(self, **kwargs):
        self.player = kwargs.get("player")
        self.restaurant = kwargs.get("restaurant")
        self.wine_database = kwargs.get("wine_database", [])
        self.rounds_played = 0
        self.total_score = 0
        self._start_round()

    def _start_round(self):
        if not self.wine_database:
            return
        self.target_wine = random.choice(self.wine_database)
        self.phase = "tasting"
        self.current_category = 0
        self.score = 0
        self.guesses = {}
        self._build_options()
        self._build_profile_bars()
        self._build_option_buttons()

    def _build_options(self):
        w = self.target_wine
        if not w:
            return

        # Correct answers
        self.correct = {
            "grape": w.primary_grape,
            "region": w.region,
            "vintage_range": self._vintage_range(w.vintage),
            "style": w.style,
        }

        # Build distractors
        all_grapes = list({wine.primary_grape for wine in random.sample(
            self.wine_database, min(200, len(self.wine_database)))})
        all_regions = list({wine.region for wine in random.sample(
            self.wine_database, min(200, len(self.wine_database)))})

        self.options = {
            "style": self._make_choices(w.style, ["Red", "White", "Rosé", "Sparkling"]),
            "grape": self._make_choices(w.primary_grape, all_grapes),
            "region": self._make_choices(w.region, all_regions),
            "vintage_range": self._make_choices(
                self._vintage_range(w.vintage),
                ["1970-1989", "1990-1999", "2000-2009", "2010-2015", "2016-2020", "2021-2023"],
            ),
        }

    def _make_choices(self, correct: str, pool: list[str], n: int = 4) -> list[str]:
        """Create n choices including the correct answer."""
        others = [x for x in pool if x != correct]
        random.shuffle(others)
        choices = [correct] + others[:n - 1]
        random.shuffle(choices)
        return choices

    def _vintage_range(self, year: int) -> str:
        if year < 1990:
            return "1970-1989"
        elif year < 2000:
            return "1990-1999"
        elif year < 2010:
            return "2000-2009"
        elif year < 2016:
            return "2010-2015"
        elif year < 2021:
            return "2016-2020"
        return "2021-2023"

    def _build_profile_bars(self):
        if not self.target_wine:
            return
        p = self.target_wine.profile
        # Add noise based on player skill
        noise = 0.0
        if self.player:
            noise = (1.0 - self.player.skills.tasting_accuracy) * 1.0

        bar_x, bar_y = 100, 250
        bar_w = 200
        attrs = {
            "Acidity": p.acidity / 5.0,
            "Tannin": p.tannin / 5.0,
            "Body": p.body / 5.0,
            "Sweetness": p.sweetness / 5.0,
            "Fruit": p.fruit_intensity / 5.0,
            "Earth": p.earth_intensity / 5.0,
            "Oak": p.oak_influence / 5.0,
        }
        self.profile_bars = {}
        for i, (name, val) in enumerate(attrs.items()):
            # Add perceptual noise
            noisy_val = max(0, min(1, val + random.gauss(0, noise * 0.15)))
            bar = ProgressBar(bar_x, bar_y + i * 28, bar_w, 14, color=COLOR_ACCENT)
            bar.value = noisy_val
            self.profile_bars[name] = bar

    def _build_option_buttons(self):
        cat = GUESS_CATEGORIES[self.current_category]
        options = self.options.get(cat, [])
        self.option_buttons = []
        start_y = 280
        for i, opt in enumerate(options):
            btn = Button(500, start_y + i * 55, 400, 45, opt,
                         callback=lambda o=opt: self._make_guess(o),
                         font_size=FONT_SIZE_BODY)
            self.option_buttons.append(btn)

    def _make_guess(self, choice: str):
        if self.phase != "tasting":
            return
        cat = GUESS_CATEGORIES[self.current_category]
        self.guesses[cat] = choice
        if choice == self.correct[cat]:
            self.score += 1

        self.current_category += 1
        if self.current_category >= len(GUESS_CATEGORIES):
            self.phase = "reveal"
            self.rounds_played += 1
            self.total_score += self.score
            # Update player stats
            if self.player:
                self.player.total_blind_tastings += 1
                self.player.wines_tasted += 1
                if self.score == len(GUESS_CATEGORIES):
                    self.player.correct_blind_tastings += 1
                skill_gain = self.score * 0.008
                self.player.skills.improve("tasting_accuracy", skill_gain)
                self.player.skills.improve("wine_knowledge", skill_gain * 0.5)
                # Learn grapes and regions
                grape = self.target_wine.primary_grape if self.target_wine else ""
                region = self.target_wine.region if self.target_wine else ""
                if grape and grape not in self.player.known_grapes:
                    self.player.known_grapes.append(grape)
                if region and region not in self.player.known_regions:
                    self.player.known_regions.append(region)
        else:
            self._build_option_buttons()

    def handle_event(self, event: pygame.event.Event):
        if self.phase == "tasting":
            for btn in self.option_buttons:
                btn.handle_event(event)
        elif self.phase == "reveal":
            self.next_btn.handle_event(event)
        self.back_btn.handle_event(event)

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        draw_text(surface, "Blind Tasting Practice", 30, 20,
                  color=COLOR_GOLD, size=FONT_SIZE_HEADING)
        draw_text(surface, f"Round {self.rounds_played + 1}  |  Score: {self.total_score}",
                  400, 25, color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)
        self.back_btn.draw(surface)

        if not self.target_wine:
            draw_text(surface, "No wines available for tasting.",
                      SCREEN_WIDTH // 2, 300, color=COLOR_TEXT_DIM,
                      size=FONT_SIZE_BODY, center=True)
            return

        # Profile panel (what you can sense)
        profile_panel = Panel(30, 70, 420, 300)
        profile_panel.draw(surface)

        draw_text(surface, "What You Perceive:", 50, 82,
                  color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_BODY)

        w = self.target_wine
        # Color hint
        draw_text(surface, f"Appearance: {w.profile.color}", 50, 110,
                  color=COLOR_TEXT, size=FONT_SIZE_SMALL)
        draw_text(surface, f"Alcohol (est): ~{w.profile.alcohol:.0f}%", 50, 132,
                  color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)

        # Aroma hints (blurred by skill)
        if w.profile.primary_aromas:
            n = max(1, int(len(w.profile.primary_aromas) *
                           (0.5 + (self.player.skills.tasting_accuracy * 0.5 if self.player else 0.3))))
            aromas = w.profile.primary_aromas[:n]
            draw_text(surface, f"Nose: {', '.join(aromas)}", 50, 155,
                      color=COLOR_TEXT, size=FONT_SIZE_SMALL, max_width=380)

        # Profile bars
        for name, bar in self.profile_bars.items():
            draw_text(surface, name, 50, bar.rect.y - 2,
                      color=COLOR_TEXT_DIM, size=FONT_SIZE_TINY)
            bar.draw(surface)

        # Guess panel
        guess_panel = Panel(470, 70, 480, 520)
        guess_panel.draw(surface)

        if self.phase == "tasting":
            cat = GUESS_CATEGORIES[self.current_category]
            labels = {
                "style": "What style is this wine?",
                "grape": "What is the primary grape?",
                "region": "Which region is this from?",
                "vintage_range": "What vintage range?",
            }
            draw_text(surface, labels.get(cat, cat), 490, 85,
                      color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_BODY)

            # Show previous guesses
            gy = 120
            for prev_cat in GUESS_CATEGORIES[:self.current_category]:
                guess = self.guesses.get(prev_cat, "?")
                is_correct = guess == self.correct[prev_cat]
                color = COLOR_SUCCESS if is_correct else COLOR_DANGER
                draw_text(surface, f"{prev_cat.title()}: {guess}", 490, gy,
                          color=color, size=FONT_SIZE_SMALL)
                gy += 22

            # Progress
            draw_text(surface, f"Question {self.current_category + 1}/{len(GUESS_CATEGORIES)}",
                      490, 240, color=COLOR_TEXT_DIM, size=FONT_SIZE_TINY)

            for btn in self.option_buttons:
                btn.draw(surface)

        elif self.phase == "reveal":
            draw_text(surface, "Results", 490, 85,
                      color=COLOR_GOLD, size=FONT_SIZE_HEADING)

            # Show the wine
            draw_text(surface, f"The wine was:", 490, 120,
                      color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)
            draw_text(surface, w.display_line, 490, 145,
                      color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_SMALL, max_width=440)
            draw_text(surface, f"Grapes: {', '.join(w.grape_names)}", 490, 170,
                      color=COLOR_TEXT, size=FONT_SIZE_SMALL)
            draw_text(surface, f"Classification: {w.classification}", 490, 192,
                      color=COLOR_GOLD, size=FONT_SIZE_SMALL)

            # Guess results
            gy = 230
            for cat in GUESS_CATEGORIES:
                guess = self.guesses.get(cat, "?")
                correct = self.correct[cat]
                is_correct = guess == correct
                color = COLOR_SUCCESS if is_correct else COLOR_DANGER
                mark = "+" if is_correct else "x"
                draw_text(surface, f"[{mark}] {cat.replace('_', ' ').title()}: {guess}",
                          490, gy, color=color, size=FONT_SIZE_SMALL)
                if not is_correct:
                    draw_text(surface, f"    Correct: {correct}", 490, gy + 18,
                              color=COLOR_TEXT_DIM, size=FONT_SIZE_TINY)
                    gy += 18
                gy += 24

            draw_text(surface, f"Score: {self.score}/{len(GUESS_CATEGORIES)}",
                      490, gy + 10, color=COLOR_GOLD, size=FONT_SIZE_HEADING)

            self.next_btn.draw(surface)

    def _next_round(self):
        self._start_round()

    def _go_back(self):
        self.game.scene_manager.switch_to(
            "hub", player=self.player, restaurant=self.restaurant,
        )
