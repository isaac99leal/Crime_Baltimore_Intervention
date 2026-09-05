import unittest

from sommelier_v2.domain import AllocationOffer, BeverageProgram, GuestProfile, InventoryLot, RelationshipAccount, WineRecord, WineStyle
from sommelier_v2.economy import bottle_price_for_target_cost, glass_price_for_target_cost
from sommelier_v2.inventory import InventoryManager
from sommelier_v2.relationships import RelationshipManager
from sommelier_v2.service import CourseProfile, recommendation_score


def wine() -> WineRecord:
    return WineRecord(
        id="w1", producer="Test Estate", label="River Block", country="France", region="Loire Valley",
        vintage=2022, style=WineStyle.WHITE, grapes=("Chenin Blanc",), wholesale_cost=20,
        rarity=0.45, acidity=4.4, tannin=1.0, body=2.7, sweetness=1.5,
    )


class EconomyTests(unittest.TestCase):
    def test_bottle_price(self):
        self.assertEqual(bottle_price_for_target_cost(30, 0.30), 100.0)

    def test_btg_price_includes_waste(self):
        no_waste = glass_price_for_target_cost(20, 0.25, expected_waste_pct=0.0)
        with_waste = glass_price_for_target_cost(20, 0.25, expected_waste_pct=0.20)
        self.assertGreater(with_waste, no_waste)


class InventoryTests(unittest.TestCase):
    def test_glass_sale_opens_and_depletes_bottle(self):
        program = BeverageProgram("Test", cash=1000, cellar_capacity_bottles=20)
        manager = InventoryManager(program)
        lot = InventoryLot("lot", wine(), 2, 20, 1, list_price_glass=14)
        manager.receive(lot)
        sale = manager.sell_glass("lot")
        self.assertTrue(sale.success)
        self.assertEqual(lot.sealed_bottles, 1)
        self.assertEqual(lot.open_bottle_ml, 600)

    def test_spoilage_removes_expired_open_wine(self):
        program = BeverageProgram("Test", cash=1000, cellar_capacity_bottles=20, day=4)
        manager = InventoryManager(program)
        lot = InventoryLot("lot", wine(), 1, 20, 1, list_price_glass=14, open_bottle_ml=300, opened_day=1, open_bottle_life_days=3)
        manager.receive(lot)
        closed = manager.close_day()
        self.assertEqual(closed.spoiled_ml, 300)
        self.assertEqual(lot.open_bottle_ml, 0)


class RelationshipTests(unittest.TestCase):
    def test_relationship_strength_improves_allocation_probability(self):
        program = BeverageProgram("Test")
        account = RelationshipAccount("d1", "Distributor")
        program.relationships[account.id] = account
        manager = RelationshipManager(program)
        offer = AllocationOffer("a1", "d1", wine(), 12, 20, scarcity=0.6, required_support_spend=10000)
        before = manager.allocation_probability(offer)
        manager.support_portfolio("d1", 8000)
        account.access += 25
        account.clamp()
        after = manager.allocation_probability(offer)
        self.assertGreater(after, before)


class ServiceTests(unittest.TestCase):
    def test_pairing_and_guest_preferences_affect_score(self):
        guest = GuestProfile("g1", "Guest", 90, preferred_styles=(WineStyle.WHITE,), preferred_grapes=("Chenin Blanc",), preferred_regions=("Loire Valley",), body_preference=2.7)
        good_course = CourseProfile("Scallop", weight=2.5, acidity=3.0, fat=3.0, protein="shellfish")
        bad_course = CourseProfile("Steak", weight=4.8, acidity=1.0, fat=4.5, protein="beef")
        good = recommendation_score(wine(), guest, good_course, 70)
        bad = recommendation_score(wine(), guest, bad_course, 70)
        self.assertGreater(good.score, bad.score)


if __name__ == "__main__":
    unittest.main()
