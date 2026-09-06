from __future__ import annotations

import unittest

from sommelier_v2.domain import BeverageProgram, InventoryLot, OpenBottleState, WineRecord, WineStyle
from sommelier_v2.inventory import InventoryManager


def wine() -> WineRecord:
    return WineRecord(
        id="wine:btg",
        producer="Test Estate",
        label="Estate Red",
        country="United States",
        region="California",
        vintage=2025,
        style=WineStyle.RED,
    )


def lot(**overrides) -> InventoryLot:
    values = dict(
        lot_id="lot:btg",
        wine=wine(),
        sealed_bottles=2,
        unit_cost=30.0,
        received_day=1,
        list_price_glass=15.0,
        bottle_ml=750,
        glass_ml=150,
        open_bottle_life_days=3,
    )
    values.update(overrides)
    return InventoryLot(**values)


class BtgOpenBottleInventoryTests(unittest.TestCase):
    def test_close_day_spoils_only_expired_open_bottle(self):
        program = BeverageProgram(name="Test", day=4)
        item = lot(
            sealed_bottles=0,
            open_bottles=[
                OpenBottleState(remaining_ml=100, opened_day=1),
                OpenBottleState(remaining_ml=600, opened_day=3),
            ],
        )
        program.inventory[item.lot_id] = item

        result = InventoryManager(program).close_day()

        self.assertEqual(result.spoiled_ml, 100)
        self.assertAlmostEqual(result.spoilage_cost, 4.0)
        self.assertEqual(result.lots_spoiled, 1)
        self.assertEqual(len(item.open_bottles), 1)
        self.assertEqual(item.open_bottles[0].remaining_ml, 600)
        self.assertEqual(item.open_bottles[0].opened_day, 3)
        self.assertEqual(item.open_bottle_ml, 600)
        self.assertEqual(item.opened_day, 3)

    def test_fifo_glass_finishes_old_bottle_before_fresh_bottle(self):
        program = BeverageProgram(name="Test", day=4)
        item = lot(
            sealed_bottles=1,
            open_bottles=[OpenBottleState(remaining_ml=100, opened_day=1)],
        )
        program.inventory[item.lot_id] = item

        result = InventoryManager(program).sell_glass(item.lot_id)

        self.assertTrue(result.success)
        self.assertEqual(item.sealed_bottles, 0)
        self.assertEqual(len(item.open_bottles), 1)
        self.assertEqual(item.open_bottles[0].remaining_ml, 700)
        self.assertEqual(item.open_bottles[0].opened_day, 4)
        self.assertEqual(item.open_bottle_ml, 700)
        self.assertEqual(item.opened_day, 4)
        self.assertAlmostEqual(result.cogs, 6.0)

    def test_fifo_depletes_oldest_of_multiple_open_bottles(self):
        program = BeverageProgram(name="Test", day=2)
        item = lot(
            sealed_bottles=0,
            glass_ml=150,
            open_bottles=[
                OpenBottleState(remaining_ml=200, opened_day=1),
                OpenBottleState(remaining_ml=500, opened_day=2),
            ],
        )
        program.inventory[item.lot_id] = item

        result = InventoryManager(program).sell_glass(item.lot_id)

        self.assertTrue(result.success)
        self.assertEqual(
            [(b.remaining_ml, b.opened_day) for b in item.open_bottles],
            [(50, 1), (500, 2)],
        )
        self.assertEqual(item.open_bottle_ml, 550)
        self.assertEqual(item.opened_day, 1)

    def test_legacy_aggregate_migrates_without_inventing_open_date(self):
        program = BeverageProgram(name="Test", day=20)
        item = lot(
            sealed_bottles=0,
            open_bottle_ml=900,
            opened_day=None,
            open_bottles=[],
        )
        program.inventory[item.lot_id] = item

        result = InventoryManager(program).close_day()

        self.assertEqual(result.spoiled_ml, 0)
        self.assertEqual(
            [(b.remaining_ml, b.opened_day) for b in item.open_bottles],
            [(750, None), (150, None)],
        )
        self.assertEqual(item.open_bottle_ml, 900)
        self.assertIsNone(item.opened_day)

    def test_per_bottle_queue_is_authoritative_for_capacity(self):
        item = lot(
            sealed_bottles=1,
            open_bottle_ml=700,
            opened_day=1,
            open_bottles=[OpenBottleState(remaining_ml=150, opened_day=1)],
        )
        self.assertAlmostEqual(item.bottle_equivalents, 1.2)

    def test_receive_rejects_future_open_date(self):
        program = BeverageProgram(name="Test", day=5)
        manager = InventoryManager(program)
        item = lot(
            sealed_bottles=0,
            open_bottles=[OpenBottleState(remaining_ml=100, opened_day=6)],
        )
        with self.assertRaises(ValueError):
            manager.receive(item)

    def test_receive_rejects_glass_larger_than_bottle(self):
        program = BeverageProgram(name="Test")
        manager = InventoryManager(program)
        with self.assertRaises(ValueError):
            manager.receive(lot(bottle_ml=100, glass_ml=150))


if __name__ == "__main__":
    unittest.main()
