"""Beverage economics: pricing, pour cost, contribution, and BTG waste."""

from __future__ import annotations

from dataclasses import dataclass


def _validate_pct(value: float, name: str) -> None:
    if value <= 0 or value >= 1:
        raise ValueError(f"{name} must be between 0 and 1")


def round_menu_price(value: float) -> float:
    return float(max(1, round(value)))


def bottle_price_for_target_cost(unit_cost: float, target_cost_pct: float = 0.30) -> float:
    _validate_pct(target_cost_pct, "target_cost_pct")
    if unit_cost < 0:
        raise ValueError("unit_cost must be non-negative")
    return round_menu_price(unit_cost / target_cost_pct)


def glass_price_for_target_cost(
    unit_cost: float,
    target_pour_cost_pct: float = 0.24,
    bottle_ml: int = 750,
    pour_ml: int = 150,
    expected_waste_pct: float = 0.08,
) -> float:
    """Return a BTG price that includes expected open-bottle waste."""
    _validate_pct(target_pour_cost_pct, "target_pour_cost_pct")
    if unit_cost < 0:
        raise ValueError("unit_cost must be non-negative")
    if bottle_ml <= 0 or pour_ml <= 0 or pour_ml > bottle_ml:
        raise ValueError("invalid bottle/pour size")
    if not 0 <= expected_waste_pct < 1:
        raise ValueError("expected_waste_pct must be in [0, 1)")

    saleable_ml = bottle_ml * (1 - expected_waste_pct)
    expected_pours = saleable_ml / pour_ml
    cost_per_expected_pour = unit_cost / expected_pours
    return round_menu_price(cost_per_expected_pour / target_pour_cost_pct)


def gross_margin_pct(revenue: float, cost: float) -> float:
    if revenue <= 0:
        return 0.0
    return max(-1.0, min(1.0, (revenue - cost) / revenue))


def pour_cost_pct(unit_cost: float, glass_price: float, bottle_ml: int = 750, pour_ml: int = 150) -> float:
    if glass_price <= 0:
        return 0.0
    pours = bottle_ml / pour_ml
    return (unit_cost / pours) / glass_price


@dataclass(frozen=True)
class BtgEconomics:
    glass_price: float
    expected_pours: float
    expected_revenue_per_bottle: float
    expected_waste_ml: float
    effective_pour_cost_pct: float
    expected_gross_profit_per_bottle: float


def btg_economics(
    unit_cost: float,
    glass_price: float,
    bottle_ml: int = 750,
    pour_ml: int = 150,
    expected_waste_pct: float = 0.08,
) -> BtgEconomics:
    if glass_price < 0 or unit_cost < 0:
        raise ValueError("prices and costs must be non-negative")
    if bottle_ml <= 0 or pour_ml <= 0:
        raise ValueError("volumes must be positive")
    if not 0 <= expected_waste_pct < 1:
        raise ValueError("expected_waste_pct must be in [0, 1)")

    expected_waste_ml = bottle_ml * expected_waste_pct
    expected_pours = (bottle_ml - expected_waste_ml) / pour_ml
    revenue = expected_pours * glass_price
    effective_cost = 0.0 if revenue <= 0 else unit_cost / revenue
    return BtgEconomics(
        glass_price=glass_price,
        expected_pours=expected_pours,
        expected_revenue_per_bottle=revenue,
        expected_waste_ml=expected_waste_ml,
        effective_pour_cost_pct=effective_cost,
        expected_gross_profit_per_bottle=revenue - unit_cost,
    )
