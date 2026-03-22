"""Guest/diner model for restaurant service."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GuestPreferences:
    """Hidden preferences that affect wine selection satisfaction."""
    preferred_colors: list[str] = field(default_factory=lambda: ["Red", "White"])
    preferred_grapes: list[str] = field(default_factory=list)
    preferred_regions: list[str] = field(default_factory=list)
    disliked_grapes: list[str] = field(default_factory=list)
    sweetness_preference: float = 1.0   # 1-5
    body_preference: float = 3.0        # 1-5
    adventure_level: float = 0.5        # 0-1, willingness to try new things
    price_ceiling: float = 200.0        # Max they'll comfortably spend per bottle
    price_floor: float = 0.0            # Min (snobs won't drink cheap wine)


@dataclass
class Guest:
    """A dining guest or table party."""
    id: str
    archetype: str               # "collector", "business", "couple", etc.
    name: str
    party_size: int = 2
    wine_knowledge: float = 0.5  # 0-1
    patience: float = 0.5        # 0-1
    generosity: float = 0.5      # 0-1 (tip multiplier)
    preferences: GuestPreferences = field(default_factory=GuestPreferences)
    # Service state
    satisfaction: float = 0.5    # 0-1, starts neutral
    courses_remaining: int = 4   # Appetizer, fish, main, cheese/dessert
    current_course: str = "aperitif"
    wines_ordered: list[str] = field(default_factory=list)  # Wine IDs
    total_spent: float = 0.0
    mood: str = "neutral"        # "impatient", "neutral", "pleased", "delighted", "annoyed"
    # Special flags
    is_critic: bool = False
    is_vip: bool = False
    has_dietary_restriction: str = ""  # "vegetarian", "vegan", "pescatarian", "kosher", "halal"
    celebration: str = ""         # "birthday", "anniversary", "promotion", "none"
    conversation_hints: list[str] = field(default_factory=list)

    @property
    def tip_multiplier(self) -> float:
        """Calculate tip based on satisfaction and generosity."""
        base = self.generosity
        if self.satisfaction > 0.8:
            return base * 1.5
        elif self.satisfaction > 0.6:
            return base * 1.2
        elif self.satisfaction < 0.3:
            return base * 0.5
        return base

    def react_to_wine(self, match_score: float):
        """Update satisfaction based on how well a wine matches preferences."""
        # match_score is 0-1
        delta = (match_score - 0.5) * 0.3  # -0.15 to +0.15 per wine
        self.satisfaction = max(0.0, min(1.0, self.satisfaction + delta))
        if self.satisfaction > 0.8:
            self.mood = "delighted"
        elif self.satisfaction > 0.6:
            self.mood = "pleased"
        elif self.satisfaction < 0.3:
            self.mood = "annoyed"
        elif self.satisfaction < 0.15:
            self.mood = "impatient"
        else:
            self.mood = "neutral"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "archetype": self.archetype,
            "name": self.name,
            "party_size": self.party_size,
            "wine_knowledge": self.wine_knowledge,
            "patience": self.patience,
            "generosity": self.generosity,
            "satisfaction": self.satisfaction,
            "courses_remaining": self.courses_remaining,
            "current_course": self.current_course,
            "wines_ordered": self.wines_ordered,
            "total_spent": self.total_spent,
            "mood": self.mood,
            "is_critic": self.is_critic,
            "is_vip": self.is_vip,
            "has_dietary_restriction": self.has_dietary_restriction,
            "celebration": self.celebration,
        }
