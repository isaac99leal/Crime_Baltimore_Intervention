"""Restaurant state model — tracks the business side."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from somm_simulator.models.wine import CellarSlot
from somm_simulator.models.player import Player
from somm_simulator.config import (
    STARTING_BUDGET, CELLAR_CAPACITY_START, TABLES_START,
)


@dataclass
class MenuItem:
    """A dish on the restaurant's food menu."""
    name: str
    course: str              # "appetizer", "fish", "main", "cheese", "dessert"
    description: str = ""
    primary_protein: str = ""  # "beef", "lamb", "fish", "poultry", "vegetable", etc.
    cooking_method: str = ""   # "grilled", "braised", "roasted", "raw", "poached"
    sauce: str = ""            # "cream", "red wine reduction", "beurre blanc", etc.
    flavor_profile: str = ""   # "rich", "delicate", "spicy", "earthy", "bright"
    weight: str = "medium"     # "light", "medium", "heavy"
    pairing_keywords: list[str] = field(default_factory=list)


@dataclass
class StaffMember:
    """A server or junior sommelier on staff."""
    name: str
    role: str = "server"         # "server", "junior_somm", "bartender"
    wine_knowledge: float = 0.2  # 0-1
    service_skill: float = 0.5   # 0-1
    reliability: float = 0.7     # 0-1, chance they show up / don't mess up
    morale: float = 0.7          # 0-1

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "wine_knowledge": self.wine_knowledge,
            "service_skill": self.service_skill,
            "reliability": self.reliability,
            "morale": self.morale,
        }


@dataclass
class FinancialRecord:
    """Track a single period's finances."""
    period: str              # "Week 1", "Month 1", etc.
    wine_revenue: float = 0.0
    wine_cost: float = 0.0
    tips_earned: float = 0.0
    spoilage_loss: float = 0.0
    purchases: float = 0.0

    @property
    def gross_profit(self) -> float:
        return self.wine_revenue - self.wine_cost

    @property
    def pour_cost_pct(self) -> float:
        if self.wine_revenue == 0:
            return 0.0
        return (self.wine_cost / self.wine_revenue) * 100

    def to_dict(self) -> dict:
        return {
            "period": self.period,
            "wine_revenue": self.wine_revenue,
            "wine_cost": self.wine_cost,
            "tips_earned": self.tips_earned,
            "spoilage_loss": self.spoilage_loss,
            "purchases": self.purchases,
        }


@dataclass
class Restaurant:
    """Full restaurant game state."""
    name: str = "Le Ciel Étoilé"
    budget: float = STARTING_BUDGET
    cellar_capacity: int = CELLAR_CAPACITY_START
    num_tables: int = TABLES_START
    cellar: list[CellarSlot] = field(default_factory=list)
    staff: list[StaffMember] = field(default_factory=list)
    menu: list[MenuItem] = field(default_factory=list)
    financial_history: list[FinancialRecord] = field(default_factory=list)
    current_period: FinancialRecord = field(default_factory=lambda: FinancialRecord(period="Week 1"))
    game_day: int = 1
    game_week: int = 1
    storage_temp_f: float = 55.0    # Cellar temperature
    storage_humidity: float = 70.0   # Cellar humidity %
    reputation_score: int = 0

    @property
    def cellar_bottles_count(self) -> int:
        return sum(slot.quantity for slot in self.cellar)

    @property
    def cellar_space_remaining(self) -> int:
        return self.cellar_capacity - self.cellar_bottles_count

    @property
    def wine_list(self) -> list[CellarSlot]:
        """Wines currently on the active wine list."""
        return [slot for slot in self.cellar if slot.on_wine_list]

    @property
    def wine_list_size(self) -> int:
        return len(self.wine_list)

    def add_to_cellar(self, slot: CellarSlot) -> bool:
        """Add wine to cellar. Returns False if no space."""
        if slot.quantity > self.cellar_space_remaining:
            return False
        # Check if we already have this wine
        for existing in self.cellar:
            if existing.wine.id == slot.wine.id:
                existing.quantity += slot.quantity
                return True
        self.cellar.append(slot)
        return True

    def sell_bottle(self, wine_id: str, price: float) -> bool:
        """Sell a bottle from the cellar. Updates financials."""
        for slot in self.cellar:
            if slot.wine.id == wine_id and slot.quantity > 0:
                slot.quantity -= 1
                self.current_period.wine_revenue += price
                self.current_period.wine_cost += slot.purchase_price
                if slot.quantity == 0:
                    self.cellar.remove(slot)
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "budget": self.budget,
            "cellar_capacity": self.cellar_capacity,
            "num_tables": self.num_tables,
            "cellar": [s.to_dict() for s in self.cellar],
            "staff": [s.to_dict() for s in self.staff],
            "game_day": self.game_day,
            "game_week": self.game_week,
            "storage_temp_f": self.storage_temp_f,
            "storage_humidity": self.storage_humidity,
            "reputation_score": self.reputation_score,
            "financial_history": [f.to_dict() for f in self.financial_history],
            "current_period": self.current_period.to_dict(),
        }
