from __future__ import annotations

import unittest

from sommelier_v2.knowledge.blend_chemistry import (
    BlendChemistryComponent,
    BlendChemistryConstraintError,
)
from sommelier_v2.knowledge.winery_blend_chemistry import (
    WineryBlendChemistryConstraintError,
    blend_winery_lots_with_chemistry,
)
from sommelier_v2.knowledge.winery_provenance import (
    ProvenanceSlice,
    WineryLot,
    WineryProvenanceError,
    WineryProvenanceLedger,
)


class WineryBlendChemistryBridgeTests(unittest.TestCase):
    @staticmethod
    def root(lot_id: str, volume_l: float, grape: str) -> WineryLot:
        return WineryLot(
            id=lot_id,
            stage="finished_bulk",
            volume_l=volume_l,
            provenance=(
                ProvenanceSlice(
                    volume_l=volume_l,
                    grape=grape,
                    country="France",
                    origins=("Burgundy",),
                    vintage=2025,
                    source_lot_ids=(lot_id,),
                ),
            ),
        )

    def ledger(self) -> WineryProvenanceLedger:
        ledger = WineryProvenanceLedger()
        ledger.add(self.root("a", 100.0, "Pinot Noir"))
        ledger.add(self.root("b", 50.0, "Pinot Noir"))
        return ledger

    @staticmethod
    def chemistry(draw_a: float = 60.0, draw_b: float = 40.0):
        return (
            BlendChemistryComponent(
                source_id="a",
                draw_l=draw_a,
                ethanol_pct=12.0,
                residual_sugar_g_l=2.0,
                malic_acid_g_l=1.0,
                dissolved_oxygen_mg_l=1.0,
            ),
            BlendChemistryComponent(
                source_id="b",
                draw_l=draw_b,
                ethanol_pct=14.0,
                residual_sugar_g_l=4.0,
                malic_acid_g_l=0.5,
                dissolved_oxygen_mg_l=2.0,
            ),
        )

    def test_same_draws_drive_physical_consumption_and_chemistry(self) -> None:
        ledger = self.ledger()
        result = blend_winery_lots_with_chemistry(
            ledger,
            ("a", "b"),
            self.chemistry(),
            new_id="blend",
            draws_l=(60.0, 40.0),
            operation_oxygen_delta_mg=0.0,
        )

        self.assertEqual(result.lot.volume_l, 100.0)
        self.assertEqual(result.chemistry.volume_l, 100.0)
        self.assertAlmostEqual(result.chemistry.ethanol_pct or 0.0, 12.8)
        self.assertEqual(result.movement.source_lot_ids, ("a", "b"))
        self.assertEqual(result.movement.source_draws_l, (60.0, 40.0))
        self.assertEqual(ledger.available_volume_l("a"), 40.0)
        self.assertEqual(ledger.available_volume_l("b"), 10.0)

    def test_chemistry_order_may_differ_but_identity_controls_alignment(self) -> None:
        ledger = self.ledger()
        a, b = self.chemistry()
        result = blend_winery_lots_with_chemistry(
            ledger,
            ("a", "b"),
            (b, a),
            new_id="blend",
            draws_l=(60.0, 40.0),
            operation_oxygen_delta_mg=0.0,
        )
        self.assertEqual(result.chemistry.source_ids, ("a", "b"))
        self.assertEqual(result.lot.parent_lot_ids, ("a", "b"))

    def test_mismatched_chemistry_draw_fails_before_inventory_mutates(self) -> None:
        ledger = self.ledger()
        before_movements = len(ledger.movements)
        with self.assertRaises(WineryBlendChemistryConstraintError):
            blend_winery_lots_with_chemistry(
                ledger,
                ("a", "b"),
                self.chemistry(draw_a=59.0),
                new_id="blend",
                draws_l=(60.0, 40.0),
                operation_oxygen_delta_mg=0.0,
            )
        self.assertEqual(ledger.available_volume_l("a"), 100.0)
        self.assertEqual(ledger.available_volume_l("b"), 50.0)
        self.assertEqual(len(ledger.movements), before_movements)
        self.assertNotIn("blend", ledger.lots)

    def test_missing_or_extra_chemistry_source_fails_before_mutation(self) -> None:
        ledger = self.ledger()
        a, _ = self.chemistry()
        with self.assertRaises(WineryBlendChemistryConstraintError):
            blend_winery_lots_with_chemistry(
                ledger,
                ("a", "b"),
                (a,),
                new_id="blend",
                draws_l=(60.0, 40.0),
                operation_oxygen_delta_mg=0.0,
            )
        self.assertEqual(ledger.available_volume_l("a"), 100.0)
        self.assertEqual(ledger.available_volume_l("b"), 50.0)

    def test_chemistry_failure_is_atomic_for_physical_ledger(self) -> None:
        ledger = self.ledger()
        with self.assertRaises(BlendChemistryConstraintError):
            blend_winery_lots_with_chemistry(
                ledger,
                ("a", "b"),
                self.chemistry(),
                new_id="blend",
                draws_l=(60.0, 40.0),
                operation_oxygen_delta_mg=-200.01,
            )
        self.assertEqual(ledger.available_volume_l("a"), 100.0)
        self.assertEqual(ledger.available_volume_l("b"), 50.0)
        self.assertNotIn("blend", ledger.lots)

    def test_physical_availability_failure_is_also_atomic(self) -> None:
        ledger = self.ledger()
        chemistry = self.chemistry(draw_a=101.0, draw_b=40.0)
        with self.assertRaises(WineryProvenanceError):
            blend_winery_lots_with_chemistry(
                ledger,
                ("a", "b"),
                chemistry,
                new_id="blend",
                draws_l=(101.0, 40.0),
                operation_oxygen_delta_mg=0.0,
            )
        self.assertEqual(ledger.available_volume_l("a"), 100.0)
        self.assertEqual(ledger.available_volume_l("b"), 50.0)
        self.assertNotIn("blend", ledger.lots)

    def test_implicit_draws_use_current_available_volume_not_original_volume(self) -> None:
        ledger = self.ledger()
        ledger.discard("a", volume_l=20.0, reason="sample_and_loss")
        rows = self.chemistry(draw_a=80.0, draw_b=50.0)
        result = blend_winery_lots_with_chemistry(
            ledger,
            ("a", "b"),
            rows,
            new_id="blend",
            operation_oxygen_delta_mg=0.0,
        )
        self.assertEqual(result.movement.source_draws_l, (80.0, 50.0))
        self.assertEqual(result.lot.volume_l, 130.0)
        self.assertEqual(ledger.available_volume_l("a"), 0.0)
        self.assertEqual(ledger.available_volume_l("b"), 0.0)

    def test_non_numeric_physical_draw_fails_before_chemistry_or_mutation(self) -> None:
        ledger = self.ledger()
        with self.assertRaises(WineryBlendChemistryConstraintError):
            blend_winery_lots_with_chemistry(
                ledger,
                ("a", "b"),
                self.chemistry(),
                new_id="blend",
                draws_l=(True, 40.0),  # type: ignore[arg-type]
                operation_oxygen_delta_mg=0.0,
            )
        self.assertEqual(ledger.available_volume_l("a"), 100.0)
        self.assertEqual(ledger.available_volume_l("b"), 50.0)


if __name__ == "__main__":
    unittest.main()
