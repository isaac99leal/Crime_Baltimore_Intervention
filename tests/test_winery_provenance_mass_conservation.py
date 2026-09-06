from __future__ import annotations

import unittest
from types import SimpleNamespace

from sommelier_v2.knowledge.winery_provenance import (
    WineryLot,
    WineryProvenanceError,
    WineryProvenanceLedger,
)


def block(block_id: str, grape: str, *, area: float = 1.0):
    return SimpleNamespace(
        id=block_id,
        grape=grape,
        area_ha=area,
        country="United States",
        region="California",
        appellation="Napa Valley",
        site_id=None,
    )


def outcome(grape: str, *, yield_hl_ha: float = 10.0):
    return SimpleNamespace(grape=grape, yield_hl_ha=yield_hl_ha, harvestable=True)


def lot(lot_id: str, grape: str = "Cabernet Sauvignon", *, volume_l: float = 1000.0) -> WineryLot:
    return WineryLot.from_vineyard(
        lot_id=lot_id,
        block=block(f"block:{lot_id}", grape),
        outcome=outcome(grape),
        vintage_year=2025,
        recovered_volume_l=volume_l,
    )


class WineryProvenanceMassConservationTests(unittest.TestCase):
    def test_blend_draw_consumes_source_balance(self):
        ledger = WineryProvenanceLedger()
        ledger.add(lot("a"))
        ledger.add(lot("b", "Merlot"))
        blend = ledger.blend(["a", "b"], new_id="blend", draws_l=[600.0, 250.0])
        self.assertAlmostEqual(blend.volume_l, 850.0)
        self.assertAlmostEqual(ledger.available_volume_l("a"), 400.0)
        self.assertAlmostEqual(ledger.available_volume_l("b"), 750.0)
        self.assertAlmostEqual(ledger.available_volume_l("blend"), 850.0)

    def test_same_source_liters_cannot_be_blended_twice(self):
        ledger = WineryProvenanceLedger()
        ledger.add(lot("a"))
        ledger.blend(["a"], new_id="first", draws_l=[800.0])
        with self.assertRaises(WineryProvenanceError):
            ledger.blend(["a"], new_id="impossible-second", draws_l=[300.0])
        self.assertNotIn("impossible-second", ledger.lots)
        self.assertAlmostEqual(ledger.available_volume_l("a"), 200.0)

    def test_transfer_consumes_input_and_records_processing_loss(self):
        ledger = WineryProvenanceLedger()
        ledger.add(lot("must"))
        child = ledger.transfer(
            "must",
            new_id="ferment",
            stage="fermentation",
            input_volume_l=700.0,
            output_volume_l=665.0,
        )
        self.assertAlmostEqual(child.volume_l, 665.0)
        self.assertAlmostEqual(ledger.available_volume_l("must"), 300.0)
        self.assertAlmostEqual(ledger.total_recorded_loss_l(), 35.0)
        movement = ledger.movements[-1]
        self.assertEqual(movement.operation, "transfer")
        self.assertAlmostEqual(movement.loss_volume_l, 35.0)

    def test_transfer_defaults_to_all_remaining_available_volume(self):
        ledger = WineryProvenanceLedger()
        ledger.add(lot("source"))
        ledger.blend(["source"], new_id="partial", draws_l=[250.0])
        moved = ledger.transfer("source", new_id="rest", stage="racking")
        self.assertAlmostEqual(moved.volume_l, 750.0)
        self.assertAlmostEqual(ledger.available_volume_l("source"), 0.0)

    def test_discard_consumes_inventory_without_descendant(self):
        ledger = WineryProvenanceLedger()
        ledger.add(lot("spoiled"))
        movement = ledger.discard("spoiled", volume_l=125.0, reason="lab-confirmed spoilage")
        self.assertIsNone(movement.output_lot_id)
        self.assertAlmostEqual(movement.loss_volume_l, 125.0)
        self.assertAlmostEqual(ledger.available_volume_l("spoiled"), 875.0)
        self.assertAlmostEqual(ledger.total_recorded_loss_l(), 125.0)

    def test_failed_blend_is_atomic_and_does_not_consume_sources(self):
        ledger = WineryProvenanceLedger()
        ledger.add(lot("a"))
        ledger.add(lot("b", "Merlot"))
        with self.assertRaises(WineryProvenanceError):
            ledger.blend(["a", "b"], new_id="bad", draws_l=[500.0, 1200.0])
        self.assertAlmostEqual(ledger.available_volume_l("a"), 1000.0)
        self.assertAlmostEqual(ledger.available_volume_l("b"), 1000.0)
        self.assertNotIn("bad", ledger.lots)
        self.assertEqual(ledger.movements, [])

    def test_failed_transfer_is_atomic(self):
        ledger = WineryProvenanceLedger()
        ledger.add(lot("source"))
        with self.assertRaises(WineryProvenanceError):
            ledger.transfer(
                "source",
                new_id="bad",
                stage="racking",
                input_volume_l=500.0,
                output_volume_l=600.0,
            )
        self.assertAlmostEqual(ledger.available_volume_l("source"), 1000.0)
        self.assertNotIn("bad", ledger.lots)

    def test_direct_add_cannot_bypass_consumption_for_present_parent(self):
        ledger = WineryProvenanceLedger()
        parent = ledger.add(lot("parent"))
        forged_child = parent.process(new_id="forged", stage="blend", output_volume_l=500.0)
        with self.assertRaises(WineryProvenanceError):
            ledger.add(forged_child)
        self.assertAlmostEqual(ledger.available_volume_l("parent"), 1000.0)

    def test_duplicate_source_in_one_blend_is_rejected(self):
        ledger = WineryProvenanceLedger()
        ledger.add(lot("a"))
        with self.assertRaises(WineryProvenanceError):
            ledger.blend(["a", "a"], new_id="duplicate", draws_l=[400.0, 400.0])
        self.assertAlmostEqual(ledger.available_volume_l("a"), 1000.0)

    def test_descendant_can_be_consumed_after_parent_is_exhausted(self):
        ledger = WineryProvenanceLedger()
        ledger.add(lot("must"))
        ferment = ledger.transfer("must", new_id="ferment", stage="fermentation")
        self.assertAlmostEqual(ledger.available_volume_l("must"), 0.0)
        bottle = ledger.transfer(
            ferment.id,
            new_id="bottled",
            stage="bottling",
            input_volume_l=900.0,
            output_volume_l=890.0,
        )
        self.assertAlmostEqual(bottle.volume_l, 890.0)
        self.assertAlmostEqual(ledger.available_volume_l("ferment"), 100.0)
        self.assertAlmostEqual(ledger.total_recorded_loss_l(), 10.0)

    def test_total_available_counts_only_live_inventory(self):
        ledger = WineryProvenanceLedger()
        ledger.add(lot("a"))
        ledger.add(lot("b", "Merlot", volume_l=500.0))
        ledger.blend(["a", "b"], new_id="blend", draws_l=[300.0, 200.0])
        # 700 + 300 remain in sources and 500 exists in the new physical blend.
        self.assertAlmostEqual(ledger.total_available_volume_l(), 1500.0)


if __name__ == "__main__":
    unittest.main()
