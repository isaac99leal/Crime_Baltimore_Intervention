"""Hub/Dashboard scene — central game screen with navigation."""

from __future__ import annotations
from typing import TYPE_CHECKING

import pygame
from somm_simulator.engine.scene_manager import Scene
from somm_simulator.ui.components import (
    Button, Panel, ProgressBar, draw_text, draw_wrapped_text,
)
from somm_simulator.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_TEXT_BRIGHT,
    COLOR_ACCENT, COLOR_ACCENT_LIGHT, COLOR_GOLD, COLOR_SUCCESS,
    COLOR_WARNING, COLOR_DANGER, COLOR_BORDER, COLOR_BG_PANEL,
    FONT_SIZE_TITLE, FONT_SIZE_HEADING, FONT_SIZE_BODY, FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
)
from somm_simulator.models.player import Player
from somm_simulator.models.restaurant import Restaurant
from somm_simulator.models.region import RegionDatabase
from somm_simulator.models.grape import GrapeDatabase
from somm_simulator.generators.wine_generator import generate_wine_database
from somm_simulator.generators.event_generator import generate_weekly_events

if TYPE_CHECKING:
    from somm_simulator.engine.game import Game


class HubScene(Scene):
    """Main game dashboard — shows stats and navigation to activities."""

    def __init__(self, game: Game):
        super().__init__(game)
        self.player: Player | None = None
        self.restaurant: Restaurant | None = None
        self.wine_database: list = []
        self.region_db: RegionDatabase | None = None
        self.grape_db: GrapeDatabase | None = None
        self.pending_events: list = []
        self.notification: str = ""
        self.notification_timer: float = 0.0

        # Navigation buttons
        btn_x = 780
        btn_w = 220
        btn_h = 52
        self.nav_buttons = [
            Button(btn_x, 160, btn_w, btn_h, "Service Night",
                   callback=self._go_service, font_size=FONT_SIZE_BODY),
            Button(btn_x, 225, btn_w, btn_h, "Wine Market",
                   callback=self._go_market, font_size=FONT_SIZE_BODY),
            Button(btn_x, 290, btn_w, btn_h, "Cellar & Wine List",
                   callback=self._go_cellar, font_size=FONT_SIZE_BODY),
            Button(btn_x, 355, btn_w, btn_h, "Blind Tasting Practice",
                   callback=self._go_tasting, font_size=FONT_SIZE_BODY),
            Button(btn_x, 420, btn_w, btn_h, "Advance Week",
                   callback=self._advance_week, font_size=FONT_SIZE_BODY),
        ]

        self.menu_btn = Button(20, 20, 100, 36, "Menu",
                               callback=self._go_menu, font_size=FONT_SIZE_SMALL)
        self.save_btn = Button(SCREEN_WIDTH - 120, 20, 100, 36, "Save",
                               callback=self._save_game, font_size=FONT_SIZE_SMALL)

        # Skill bars
        self.skill_bars: dict[str, ProgressBar] = {}

    def enter(self, **kwargs):
        if "player" in kwargs:
            self.player = kwargs["player"]
        if "restaurant" in kwargs:
            self.restaurant = kwargs["restaurant"]

        if kwargs.get("is_new"):
            self._init_new_game()

        if "save_data" in kwargs:
            self._load_from_save(kwargs["save_data"])

        # Rebuild skill bars
        if self.player:
            skills = self.player.skills
            bar_x, bar_y = 90, 470
            bar_w = 160
            self.skill_bars = {
                "tasting": ProgressBar(bar_x, bar_y, bar_w, color=COLOR_ACCENT),
                "service": ProgressBar(bar_x, bar_y + 28, bar_w, color=COLOR_SUCCESS),
                "knowledge": ProgressBar(bar_x, bar_y + 56, bar_w, color=COLOR_GOLD),
                "business": ProgressBar(bar_x, bar_y + 84, bar_w, color=COLOR_WARNING),
                "sales": ProgressBar(bar_x, bar_y + 112, bar_w, color=COLOR_ACCENT_LIGHT),
            }
            self.skill_bars["tasting"].value = skills.tasting_accuracy
            self.skill_bars["service"].value = skills.service_grace
            self.skill_bars["knowledge"].value = skills.wine_knowledge
            self.skill_bars["business"].value = skills.business_acumen
            self.skill_bars["sales"].value = skills.salesmanship

    def _init_new_game(self):
        """Set up a new game with generated wine database."""
        self.region_db = RegionDatabase()
        self.grape_db = GrapeDatabase()
        self.wine_database = generate_wine_database(
            self.region_db, self.grape_db, target_count=2000, seed=42,
        )
        self.notification = f"Welcome! {len(self.wine_database)} wines available on the market."
        self.notification_timer = 5.0

    def _load_from_save(self, save_data: dict):
        from somm_simulator.models.player import Player
        from somm_simulator.models.restaurant import Restaurant
        state = save_data.get("game_state", {})
        self.player = Player.from_dict(state["player"])
        # Restaurant loading simplified — just restore key fields
        r_data = state.get("restaurant", {})
        self.restaurant = Restaurant(
            name=r_data.get("name", "Le Ciel Étoilé"),
            budget=r_data.get("budget", 15000),
            game_day=r_data.get("game_day", 1),
            game_week=r_data.get("game_week", 1),
        )
        self.region_db = RegionDatabase()
        self.grape_db = GrapeDatabase()
        self.wine_database = generate_wine_database(
            self.region_db, self.grape_db, target_count=2000, seed=42,
        )

    def handle_event(self, event: pygame.event.Event):
        for btn in self.nav_buttons:
            btn.handle_event(event)
        self.menu_btn.handle_event(event)
        self.save_btn.handle_event(event)

    def update(self, dt: float):
        if self.notification_timer > 0:
            self.notification_timer -= dt

    def draw(self, surface: pygame.Surface):
        if not self.player or not self.restaurant:
            draw_text(surface, "Loading...", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                      color=COLOR_TEXT_DIM, size=FONT_SIZE_HEADING, center=True)
            return

        self.menu_btn.draw(surface)
        self.save_btn.draw(surface)

        # Left panel — Player info
        left_panel = Panel(30, 70, 340, 240)
        left_panel.draw(surface)

        draw_text(surface, self.player.name, 50, 82,
                  color=COLOR_GOLD, size=FONT_SIZE_HEADING)
        draw_text(surface, self.player.title, 50, 112,
                  color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)

        # Stats
        sy = 145
        stats = [
            f"Reputation: {self.player.reputation}",
            f"Services Completed: {self.player.services_completed}",
            f"Wines Tasted: {self.player.wines_tasted}",
            f"Blind Tasting: {self.player.blind_tasting_accuracy:.0%}",
            f"Tips Earned: ${self.player.total_tips:,.0f}",
        ]
        for s in stats:
            draw_text(surface, s, 50, sy, color=COLOR_TEXT, size=FONT_SIZE_SMALL)
            sy += 22

        if self.player.can_promote:
            draw_text(surface, "PROMOTION AVAILABLE!", 50, sy + 5,
                      color=COLOR_SUCCESS, size=FONT_SIZE_SMALL)

        # Restaurant panel
        rest_panel = Panel(30, 320, 340, 120)
        rest_panel.draw(surface)
        draw_text(surface, self.restaurant.name, 50, 332,
                  color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_BODY)
        draw_text(surface, f"Week {self.restaurant.game_week}, Day {self.restaurant.game_day}",
                  50, 358, color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)
        draw_text(surface, f"Budget: ${self.restaurant.budget:,.0f}", 50, 380,
                  color=COLOR_GOLD, size=FONT_SIZE_BODY)
        draw_text(surface, f"Cellar: {self.restaurant.cellar_bottles_count}/{self.restaurant.cellar_capacity} bottles",
                  50, 406, color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)

        # Skills panel
        skill_panel = Panel(30, 450, 340, 175)
        skill_panel.draw(surface)
        draw_text(surface, "Skills", 50, 452, color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_SMALL)

        labels = {
            "tasting": "Tasting",
            "service": "Service",
            "knowledge": "Knowledge",
            "business": "Business",
            "sales": "Sales",
        }
        for key, bar in self.skill_bars.items():
            draw_text(surface, labels[key], 50, bar.rect.y - 2,
                      color=COLOR_TEXT_DIM, size=FONT_SIZE_TINY)
            bar.draw(surface)
            pct = f"{bar.value:.0%}"
            draw_text(surface, pct, bar.rect.right + 8, bar.rect.y - 2,
                      color=COLOR_TEXT_DIM, size=FONT_SIZE_TINY)

        # Navigation panel
        nav_panel = Panel(760, 70, 260, 420)
        nav_panel.draw(surface)
        draw_text(surface, "Activities", 780, 85, color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_BODY)

        # Separator
        pygame.draw.line(surface, COLOR_BORDER, (780, 112), (1000, 112))

        # Description area
        descs = [
            "Serve guests and earn tips & reputation",
            "Browse and purchase wines for your cellar",
            "Manage your cellar and wine list",
            "Practice identifying wines blind",
            "Progress time and trigger events",
        ]
        mouse_pos = pygame.mouse.get_pos()
        for i, btn in enumerate(self.nav_buttons):
            btn.draw(surface)
            if btn.rect.collidepoint(mouse_pos):
                draw_text(surface, descs[i], 780, 500,
                          color=COLOR_TEXT_DIM, size=FONT_SIZE_TINY)

        # Notification
        if self.notification and self.notification_timer > 0:
            alpha = min(1.0, self.notification_timer)
            c = tuple(int(v * alpha) for v in COLOR_GOLD)
            draw_text(surface, self.notification, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40,
                      color=c, size=FONT_SIZE_SMALL, center=True)

        # Wine list status
        wl_count = self.restaurant.wine_list_size
        draw_text(surface, f"Wine List: {wl_count} selections",
                  780, 540, color=COLOR_TEXT_DIM, size=FONT_SIZE_SMALL)

    def _go_service(self):
        if self.restaurant and self.restaurant.wine_list_size == 0:
            self.notification = "Add wines to your wine list first!"
            self.notification_timer = 3.0
            return
        self.game.scene_manager.switch_to(
            "service",
            player=self.player, restaurant=self.restaurant,
            wine_database=self.wine_database,
        )

    def _go_market(self):
        self.game.scene_manager.switch_to(
            "market",
            player=self.player, restaurant=self.restaurant,
            wine_database=self.wine_database,
            region_db=self.region_db, grape_db=self.grape_db,
        )

    def _go_cellar(self):
        self.game.scene_manager.switch_to(
            "cellar",
            player=self.player, restaurant=self.restaurant,
        )

    def _go_tasting(self):
        self.game.scene_manager.switch_to(
            "tasting",
            player=self.player, restaurant=self.restaurant,
            wine_database=self.wine_database,
        )

    def _advance_week(self):
        if not self.restaurant or not self.player:
            return
        self.restaurant.game_week += 1
        self.restaurant.game_day += 7

        events = generate_weekly_events(
            self.player.career_stage, self.restaurant.game_week,
        )
        if events:
            self.game.scene_manager.switch_to(
                "week_summary",
                player=self.player, restaurant=self.restaurant,
                events=events, wine_database=self.wine_database,
                region_db=self.region_db, grape_db=self.grape_db,
            )
        else:
            self.notification = f"Week {self.restaurant.game_week} — quiet week, no events."
            self.notification_timer = 3.0

    def _go_menu(self):
        self.game.scene_manager.switch_to("main_menu")

    def _save_game(self):
        if not self.player or not self.restaurant:
            return
        state = {
            "player": self.player.to_dict(),
            "restaurant": self.restaurant.to_dict(),
        }
        self.game.save_system.save(state, slot_name=self.player.name)
        self.notification = "Game saved!"
        self.notification_timer = 3.0
