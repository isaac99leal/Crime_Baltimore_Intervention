"""Guest engagement, pairing, and recommendation scoring."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .domain import GuestProfile, InventoryLot, WineRecord, WineStyle
from .inventory import InventoryManager, SaleResult


@dataclass(frozen=True)
class CourseProfile:
    name: str
    weight: float = 3.0
    richness: float = 3.0
    sweetness: float = 1.0
    acidity: float = 2.5
    spice: float = 1.0
    fat: float = 2.0
    protein: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecommendationResult:
    score: float
    guest_fit: float
    pairing_fit: float
    value_fit: float
    prestige_fit: float
    explanation: tuple[str, ...]


@dataclass(frozen=True)
class ServiceOutcome:
    sale: SaleResult
    satisfaction_delta: float
    reputation_delta: float
    recommendation: RecommendationResult


def _closeness(value: float, target: float, spread: float = 4.0) -> float:
    return max(0.0, 1.0 - abs(value - target) / spread)


def _price_fit(price: float, budget: float, value_sensitivity: float) -> float:
    if budget <= 0:
        return 0.5
    ratio = price / budget
    if ratio <= 1:
        value_bonus = (1 - ratio) * 0.15 * value_sensitivity
        return min(1.0, 0.85 + value_bonus)
    over = ratio - 1
    return max(0.0, 0.85 - over * (0.9 + value_sensitivity * 0.6))


def _pairing_fit(wine: WineRecord, course: CourseProfile) -> float:
    body = _closeness(wine.body, course.weight)
    acid_need = min(5.0, 2.0 + course.fat * 0.6 + course.acidity * 0.2)
    acidity = _closeness(wine.acidity, acid_need)
    sweetness_need = max(course.sweetness, course.spice * 0.45)
    sweetness = _closeness(wine.sweetness, sweetness_need, spread=3.0)

    tannin = 0.8
    if course.protein.lower() in {"beef", "lamb", "venison", "duck"}:
        tannin = _closeness(wine.tannin, 3.8)
    elif course.protein.lower() in {"fish", "shellfish"}:
        tannin = _closeness(wine.tannin, 1.3)

    style_bonus = 0.0
    tags = {t.lower() for t in course.tags}
    if "fried" in tags and wine.style == WineStyle.SPARKLING:
        style_bonus += 0.08
    if "spicy" in tags and wine.sweetness >= 2.0:
        style_bonus += 0.08
    if "dessert" in tags and wine.sweetness >= course.sweetness:
        style_bonus += 0.12

    return max(0.0, min(1.0, (body * 0.28 + acidity * 0.27 + sweetness * 0.20 + tannin * 0.25) + style_bonus))


def recommendation_score(wine: WineRecord, guest: GuestProfile, course: CourseProfile, price: float) -> RecommendationResult:
    style_fit = 0.65 if not guest.preferred_styles else (1.0 if wine.style in guest.preferred_styles else 0.45)
    grape_fit = 0.65 if not guest.preferred_grapes else (1.0 if any(g in guest.preferred_grapes for g in wine.grapes) else 0.45)
    region_fit = 0.65 if not guest.preferred_regions else (1.0 if wine.region in guest.preferred_regions or wine.country in guest.preferred_regions else 0.45)
    body_fit = _closeness(wine.body, guest.body_preference)
    sweet_fit = _closeness(wine.sweetness, guest.sweetness_preference, spread=3.0)
    novelty = max(0.0, min(1.0, wine.rarity * 0.6 + (1.0 if wine.grapes and any(g not in {"Cabernet Sauvignon", "Merlot", "Chardonnay", "Pinot Noir"} for g in wine.grapes) else 0.0) * 0.4))
    adventure_fit = 1.0 - abs(novelty - guest.adventurousness)

    guest_fit = style_fit * 0.22 + grape_fit * 0.16 + region_fit * 0.14 + body_fit * 0.18 + sweet_fit * 0.10 + adventure_fit * 0.20
    pairing_fit = _pairing_fit(wine, course)
    value_fit = _price_fit(price, guest.budget_per_bottle, guest.value_sensitivity)
    prestige_fit = max(0.0, min(1.0, 0.35 + wine.rarity * 0.65))
    prestige_fit = prestige_fit * guest.prestige_sensitivity + 0.65 * (1 - guest.prestige_sensitivity)
    score = max(0.0, min(1.0, guest_fit * 0.38 + pairing_fit * 0.34 + value_fit * 0.18 + prestige_fit * 0.10))

    notes = [f"guest fit {guest_fit:.0%}", f"pairing fit {pairing_fit:.0%}", f"value fit {value_fit:.0%}"]
    if wine.rarity > 0.75:
        notes.append("rare bottle adds prestige but may raise expectation")
    if guest.adventurousness > 0.7 and adventure_fit > 0.75:
        notes.append("guest is receptive to an unusual recommendation")
    return RecommendationResult(score, guest_fit, pairing_fit, value_fit, prestige_fit, tuple(notes))


class ServiceEngine:
    def __init__(self, inventory: InventoryManager):
        self.inventory = inventory

    def sell_recommendation(self, lot: InventoryLot, guest: GuestProfile, course: CourseProfile, channel: str = "bottle") -> ServiceOutcome:
        if channel == "btg":
            price = lot.list_price_glass
            sale = self.inventory.sell_glass(lot.lot_id)
            equivalent_bottle_price = price * (lot.bottle_ml / lot.glass_ml)
            recommendation = recommendation_score(lot.wine, guest, course, equivalent_bottle_price)
        else:
            price = lot.list_price_bottle
            sale = self.inventory.sell_bottle(lot.lot_id)
            recommendation = recommendation_score(lot.wine, guest, course, price)

        if not sale.success:
            return ServiceOutcome(sale, -0.06, -0.02, recommendation)
        centered = recommendation.score - 0.5
        satisfaction_delta = math.tanh(centered * 3.0) * 0.22
        reputation_delta = max(-0.08, min(0.10, centered * 0.12))
        return ServiceOutcome(sale, satisfaction_delta, reputation_delta, recommendation)
