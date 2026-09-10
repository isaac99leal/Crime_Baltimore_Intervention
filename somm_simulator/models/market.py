"""Supplier buying rules for the playable market.

Discounts and freight are explicit game balance rules, not real supplier quotes.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import math

from .wine import CellarSlot


@dataclass(frozen=True)
class PurchaseQuote:
    quantity: int
    discount_pct: int
    wine_cost: float
    freight: float
    total: float

    @property
    def landed_unit_cost(self):
        return self.total / self.quantity


def quote_purchase(unit_cost: float, quantity: int) -> PurchaseQuote:
    if type(quantity) is not int or quantity <= 0:
        raise ValueError("Quantity must be a positive whole number")
    if not math.isfinite(unit_cost) or unit_cost < 0:
        raise ValueError("Wholesale cost must be finite and non-negative")
    discount = 5 if quantity >= 12 else 3 if quantity >= 6 else 0
    wine_cost = (Decimal(str(unit_cost)) * quantity * Decimal(100 - discount) / 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    freight = Decimal("0") if quantity >= 12 else Decimal("12")
    return PurchaseQuote(quantity, discount, float(wine_cost), float(freight), float(wine_cost + freight))


def weekly_offerings(wines, week: int, limit: int = 120):
    """Stable offers across visits, refreshes, catalog order, and save reloads."""
    unique = {wine.id: wine for wine in wines}
    return sorted(unique.values(), key=lambda wine: (
        sha256(f"market:{week}:{wine.id}".encode()).digest(), wine.id
    ))[:max(0, limit)]


def purchase_wine(restaurant, wine, quantity: int) -> PurchaseQuote:
    quote = quote_purchase(wine.wholesale_cost, quantity)
    if quote.total > restaurant.budget:
        raise ValueError(f"Not enough budget. Need ${quote.total:.2f}")
    if quantity > restaurant.cellar_space_remaining:
        raise ValueError(f"Not enough cellar space. Need {quantity} slots")
    if quantity > wine.quantity_available:
        raise ValueError(f"Only {wine.quantity_available} bottles available")
    slot = CellarSlot(wine=wine, quantity=quantity, purchase_price=quote.landed_unit_cost,
                      date_acquired=restaurant.game_day)
    if not restaurant.add_to_cellar(slot):
        raise ValueError("Not enough cellar space")
    restaurant.budget -= quote.total
    restaurant.current_period.purchases += quote.total
    wine.quantity_available -= quantity
    return quote
