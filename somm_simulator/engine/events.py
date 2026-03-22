"""Custom event system for game-wide communication."""

from collections import defaultdict
from typing import Callable, Any


class EventBus:
    """Simple pub/sub event system for decoupled communication."""

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable):
        """Register a callback for an event type."""
        self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """Remove a callback."""
        if event_type in self._listeners:
            self._listeners[event_type] = [
                cb for cb in self._listeners[event_type] if cb != callback
            ]

    def emit(self, event_type: str, **data: Any):
        """Fire an event, calling all registered listeners."""
        for callback in self._listeners.get(event_type, []):
            callback(**data)

    def clear(self):
        """Remove all listeners."""
        self._listeners.clear()


# Global event bus instance
game_events = EventBus()
