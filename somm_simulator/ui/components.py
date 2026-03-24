"""Reusable UI components — buttons, panels, text rendering, scroll lists."""

from __future__ import annotations
import pygame
from somm_simulator.config import (
    COLOR_TEXT, COLOR_TEXT_DIM, COLOR_TEXT_BRIGHT, COLOR_BG_PANEL,
    COLOR_BG_PANEL_HOVER, COLOR_BG_PANEL_SELECTED, COLOR_ACCENT,
    COLOR_ACCENT_LIGHT, COLOR_GOLD, COLOR_BORDER, COLOR_SCROLLBAR,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    FONT_SIZE_TITLE, FONT_SIZE_HEADING, FONT_SIZE_BODY, FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
)

# Font cache
_fonts: dict[int, pygame.font.Font] = {}


def get_font(size: int) -> pygame.font.Font:
    """Get or create a cached font at the given size."""
    if size not in _fonts:
        _fonts[size] = pygame.font.SysFont("Georgia", size)
    return _fonts[size]


def draw_text(
    surface: pygame.Surface,
    text: str,
    x: int,
    y: int,
    color: tuple = COLOR_TEXT,
    size: int = FONT_SIZE_BODY,
    center: bool = False,
    max_width: int = 0,
) -> pygame.Rect:
    """Draw text and return its rect."""
    font = get_font(size)
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    if max_width and rect.width > max_width:
        # Truncate with ellipsis
        while rect.width > max_width and len(text) > 3:
            text = text[:-4] + "..."
            rendered = font.render(text, True, color)
            rect = rendered.get_rect()
            if center:
                rect.center = (x, y)
            else:
                rect.topleft = (x, y)
    surface.blit(rendered, rect)
    return rect


def draw_wrapped_text(
    surface: pygame.Surface,
    text: str,
    x: int,
    y: int,
    max_width: int,
    color: tuple = COLOR_TEXT,
    size: int = FONT_SIZE_BODY,
    line_spacing: int = 4,
) -> int:
    """Draw word-wrapped text. Returns total height used."""
    font = get_font(size)
    words = text.split(" ")
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        if font.size(test)[0] <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    total_h = 0
    for line in lines:
        rendered = font.render(line, True, color)
        surface.blit(rendered, (x, y + total_h))
        total_h += rendered.get_height() + line_spacing
    return total_h


class Button:
    """A clickable button with hover effects."""

    def __init__(
        self,
        x: int, y: int, w: int, h: int,
        text: str,
        callback=None,
        color_bg: tuple = COLOR_BG_PANEL,
        color_hover: tuple = COLOR_BG_PANEL_HOVER,
        color_text: tuple = COLOR_TEXT,
        font_size: int = FONT_SIZE_BODY,
        border_color: tuple = COLOR_BORDER,
        enabled: bool = True,
    ):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback
        self.color_bg = color_bg
        self.color_hover = color_hover
        self.color_text = color_text
        self.font_size = font_size
        self.border_color = border_color
        self.enabled = enabled
        self.hovered = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle event. Returns True if button was clicked."""
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def draw(self, surface: pygame.Surface):
        bg = self.color_hover if self.hovered and self.enabled else self.color_bg
        if not self.enabled:
            bg = (25, 25, 30)
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, self.border_color, self.rect, 1, border_radius=6)
        tc = self.color_text if self.enabled else COLOR_TEXT_DIM
        draw_text(surface, self.text, self.rect.centerx, self.rect.centery,
                  color=tc, size=self.font_size, center=True)


class Panel:
    """A rectangular panel/card background."""

    def __init__(self, x: int, y: int, w: int, h: int,
                 color: tuple = COLOR_BG_PANEL, border: tuple = COLOR_BORDER):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.border = border

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=8)
        pygame.draw.rect(surface, self.border, self.rect, 1, border_radius=8)


class ScrollList:
    """A scrollable list of selectable items."""

    def __init__(self, x: int, y: int, w: int, h: int, item_height: int = 36):
        self.rect = pygame.Rect(x, y, w, h)
        self.item_height = item_height
        self.items: list[dict] = []  # {"text": str, "data": any, "color": tuple}
        self.scroll_offset = 0
        self.selected_index = -1
        self.hovered_index = -1

    def set_items(self, items: list[dict]):
        self.items = items
        self.scroll_offset = 0
        self.selected_index = -1

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        """Handle event. Returns selected item dict if clicked."""
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            max_scroll = max(0, len(self.items) * self.item_height - self.rect.height)
            self.scroll_offset = max(0, min(max_scroll, self.scroll_offset - event.y * 30))
        elif event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self.rect.y + self.scroll_offset
                self.hovered_index = rel_y // self.item_height
            else:
                self.hovered_index = -1
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self.rect.y + self.scroll_offset
                idx = rel_y // self.item_height
                if 0 <= idx < len(self.items):
                    self.selected_index = idx
                    return self.items[idx]
        return None

    def draw(self, surface: pygame.Surface):
        # Clip to our area
        clip = surface.get_clip()
        surface.set_clip(self.rect)
        pygame.draw.rect(surface, COLOR_BG_PANEL, self.rect, border_radius=4)

        for i, item in enumerate(self.items):
            iy = self.rect.y + i * self.item_height - self.scroll_offset
            if iy + self.item_height < self.rect.y or iy > self.rect.bottom:
                continue
            item_rect = pygame.Rect(self.rect.x, iy, self.rect.width - 12, self.item_height)

            # Background
            if i == self.selected_index:
                pygame.draw.rect(surface, COLOR_BG_PANEL_SELECTED, item_rect)
            elif i == self.hovered_index:
                pygame.draw.rect(surface, COLOR_BG_PANEL_HOVER, item_rect)

            # Text
            color = item.get("color", COLOR_TEXT)
            draw_text(surface, item.get("text", ""), item_rect.x + 8, item_rect.y + 8,
                      color=color, size=FONT_SIZE_SMALL, max_width=item_rect.width - 16)

            # Separator
            pygame.draw.line(surface, COLOR_BORDER,
                             (item_rect.x, item_rect.bottom),
                             (item_rect.right, item_rect.bottom))

        # Scrollbar
        if len(self.items) * self.item_height > self.rect.height:
            total_h = len(self.items) * self.item_height
            bar_h = max(20, int(self.rect.height * self.rect.height / total_h))
            bar_y = self.rect.y + int(self.scroll_offset / total_h * self.rect.height)
            bar_rect = pygame.Rect(self.rect.right - 8, bar_y, 6, bar_h)
            pygame.draw.rect(surface, COLOR_SCROLLBAR, bar_rect, border_radius=3)

        pygame.draw.rect(surface, COLOR_BORDER, self.rect, 1, border_radius=4)
        surface.set_clip(clip)


class ProgressBar:
    """A horizontal progress bar."""

    def __init__(self, x: int, y: int, w: int, h: int = 12,
                 color: tuple = COLOR_ACCENT, bg: tuple = COLOR_BG_PANEL):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.bg = bg
        self.value = 0.0  # 0-1

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, self.bg, self.rect, border_radius=4)
        if self.value > 0:
            fill_w = int(self.rect.width * min(1.0, self.value))
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height)
            pygame.draw.rect(surface, self.color, fill_rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_BORDER, self.rect, 1, border_radius=4)


class TextInput:
    """Simple single-line text input field."""

    def __init__(self, x: int, y: int, w: int, h: int = 40,
                 placeholder: str = "", max_length: int = 30):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = ""
        self.placeholder = placeholder
        self.max_length = max_length
        self.active = False
        self.cursor_blink = 0.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True if Enter was pressed."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode and len(self.text) < self.max_length:
                if event.unicode.isprintable():
                    self.text += event.unicode
        return False

    def update(self, dt: float):
        self.cursor_blink += dt

    def draw(self, surface: pygame.Surface):
        border = COLOR_ACCENT if self.active else COLOR_BORDER
        pygame.draw.rect(surface, COLOR_BG_PANEL, self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=6)

        if self.text:
            draw_text(surface, self.text, self.rect.x + 10, self.rect.centery - 9,
                      color=COLOR_TEXT_BRIGHT, size=FONT_SIZE_BODY)
        elif not self.active:
            draw_text(surface, self.placeholder, self.rect.x + 10, self.rect.centery - 9,
                      color=COLOR_TEXT_DIM, size=FONT_SIZE_BODY)

        # Cursor
        if self.active and int(self.cursor_blink * 2) % 2 == 0:
            font = get_font(FONT_SIZE_BODY)
            cx = self.rect.x + 10 + font.size(self.text)[0]
            pygame.draw.line(surface, COLOR_TEXT_BRIGHT,
                             (cx, self.rect.y + 8), (cx, self.rect.bottom - 8), 2)


class TabBar:
    """Horizontal tab selector."""

    def __init__(self, x: int, y: int, w: int, tabs: list[str]):
        self.x = x
        self.y = y
        self.w = w
        self.tabs = tabs
        self.active_tab = 0
        self.tab_rects: list[pygame.Rect] = []
        self._build_rects()

    def _build_rects(self):
        tw = self.w // max(1, len(self.tabs))
        self.tab_rects = [
            pygame.Rect(self.x + i * tw, self.y, tw, 36)
            for i in range(len(self.tabs))
        ]

    def handle_event(self, event: pygame.event.Event) -> int | None:
        """Returns tab index if clicked, else None."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.tab_rects):
                if r.collidepoint(event.pos):
                    self.active_tab = i
                    return i
        return None

    def draw(self, surface: pygame.Surface):
        for i, (tab, rect) in enumerate(zip(self.tabs, self.tab_rects)):
            bg = COLOR_ACCENT if i == self.active_tab else COLOR_BG_PANEL
            tc = COLOR_TEXT_BRIGHT if i == self.active_tab else COLOR_TEXT_DIM
            pygame.draw.rect(surface, bg, rect)
            pygame.draw.rect(surface, COLOR_BORDER, rect, 1)
            draw_text(surface, tab, rect.centerx, rect.centery,
                      color=tc, size=FONT_SIZE_SMALL, center=True)
