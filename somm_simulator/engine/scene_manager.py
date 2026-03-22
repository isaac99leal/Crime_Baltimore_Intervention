"""Scene management — handles transitions between game screens."""

from __future__ import annotations
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from somm_simulator.engine.game import Game


class Scene:
    """Base class for all game scenes."""

    def __init__(self, game: Game):
        self.game = game

    def enter(self, **kwargs):
        """Called when this scene becomes active."""
        pass

    def exit(self):
        """Called when leaving this scene."""
        pass

    def handle_event(self, event: pygame.event.Event):
        """Process a single pygame event."""
        pass

    def update(self, dt: float):
        """Update game logic. dt is seconds since last frame."""
        pass

    def draw(self, surface: pygame.Surface):
        """Render the scene."""
        pass


class SceneManager:
    """Manages scene stack and transitions."""

    def __init__(self, game: Game):
        self.game = game
        self._scenes: dict[str, Scene] = {}
        self._active_scene: Scene | None = None
        self._scene_stack: list[str] = []

    def register(self, name: str, scene: Scene):
        """Register a scene by name."""
        self._scenes[name] = scene

    def switch_to(self, name: str, **kwargs):
        """Switch to a named scene, replacing the current one."""
        if self._active_scene:
            self._active_scene.exit()
        self._active_scene = self._scenes[name]
        self._scene_stack = [name]
        self._active_scene.enter(**kwargs)

    def push(self, name: str, **kwargs):
        """Push a scene onto the stack (overlay)."""
        if self._active_scene:
            self._active_scene.exit()
        self._scene_stack.append(name)
        self._active_scene = self._scenes[name]
        self._active_scene.enter(**kwargs)

    def pop(self):
        """Pop the top scene and return to the previous one."""
        if self._active_scene:
            self._active_scene.exit()
        if self._scene_stack:
            self._scene_stack.pop()
        if self._scene_stack:
            name = self._scene_stack[-1]
            self._active_scene = self._scenes[name]
            self._active_scene.enter()
        else:
            self._active_scene = None

    def handle_event(self, event: pygame.event.Event):
        if self._active_scene:
            self._active_scene.handle_event(event)

    def update(self, dt: float):
        if self._active_scene:
            self._active_scene.update(dt)

    def draw(self, surface: pygame.Surface):
        if self._active_scene:
            self._active_scene.draw(surface)
