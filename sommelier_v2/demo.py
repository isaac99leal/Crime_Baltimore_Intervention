"""Small vertical-slice demo for the v2 simulation engine."""

from __future__ import annotations

from .domain import BeverageProgram, GuestProfile, InventoryLot, WineRecord, WineStyle
from .economy import bottle_price_for_target_cost, glass_price_for_target_cost
from .service import CourseProfile
from .simulation import RestaurantSimulation


def build_demo() -> RestaurantSimulation:
    program = BeverageProgram(name="Atelier 17", cash=12_000, cellar_capacity_bottles=120)
    sim = RestaurantSimulation(program)
    wine = WineRecord(
        id="demo-chenin-2022", producer="Maison Varenne", label="Les Hautes Rives",
        country="France", region="Loire Valley", appellation="Saumur", vintage=2022,
        style=WineStyle.WHITE, grapes=("Chenin Blanc",), wholesale_cost=18.0, rarity=0.35,
        acidity=4.3, tannin=1.0, body=2.8, sweetness=1.4,
        aromas=("quince", "yellow apple", "beeswax"),
    )
    lot = InventoryLot("lot-001", wine, 12, 18.0, 1)
    lot.list_price_bottle = bottle_price_for_target_cost(lot.unit_cost, 0.30)
    lot.list_price_glass = glass_price_for_target_cost(lot.unit_cost, 0.24)
    lot.listed_bottle = True
    lot.listed_btg = True
    sim.buy_lot(lot)
    return sim


def main() -> None:
    sim = build_demo()
    lot = sim.program.inventory["lot-001"]
    guest = GuestProfile(
        id="guest-1", name="Mara Chen", budget_per_bottle=85,
        preferred_styles=(WineStyle.WHITE, WineStyle.SPARKLING),
        preferred_grapes=("Chenin Blanc", "Riesling"), preferred_regions=("Loire Valley",),
        body_preference=2.7, adventurousness=0.65,
    )
    course = CourseProfile("Roasted scallops, brown butter, apple", weight=2.5, richness=3.2, acidity=2.8, fat=3.2, protein="shellfish", tags=("roasted",))
    outcome = sim.service.sell_recommendation(lot, guest, course, channel="btg")
    sim.record_sale(outcome.sale.revenue, outcome.sale.cogs, lot.wine.display_name)
    print(lot.wine.display_name)
    print(f"Recommendation: {outcome.recommendation.score:.0%}")
    print(f"Glass sale: ${outcome.sale.revenue:.2f}")
    print(f"Cash: ${sim.program.cash:.2f}")
    print(f"Open bottle remaining: {lot.open_bottle_ml} ml")


if __name__ == "__main__":
    main()
