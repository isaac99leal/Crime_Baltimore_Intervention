from __future__ import annotations

import unittest

from sommelier_v2.knowledge.bottling_lot import (
    BottlingLotConstraintError,
    bottle_winery_lot,
)
from sommelier_v2.knowledge.packaging import PackagingAssessment
from sommelier_v2.knowledge.winery_provenance import (
    ProvenanceSlice,
    WineryLot,
    WineryProvenanceError,
    WineryProvenanceLedger,
)


def assessment(*, complete: bool = True) -> PackagingAssessment:
    return PackagingAssessment(
        prebottling_oxygen_risk_index=0.10 if complete else None,
        closure_oxygen_exposure_prior=0.20 if complete else None,
        oxygen_assessment_complete=complete,
        ageing_oxygen_modifier=1.20 if complete else 1.0,
        free_so2_cost_guide_upper_mg_l=1.0 if complete else None,
        molecular_so2_before_packaging_mg_l=0.50,
        tartrate_test_status="tested_stable",
        tartrate_physical_instability_risk=0.0,
        warnings=() if complete else ("oxygen evidence incomplete",),
        evidence_record_ids=(),
    )


def bulk(lot_id: str = "bulk", *, volume_l: float = 100.0) -> WineryLot:
    return WineryLot(
        id=lot_id,
        stage="finished_wine",
        volume_l=volume_l,
        provenance=(
            ProvenanceSlice(
                volume_l=volume_l,
                grape="Pinot Noir",
                country="United States",
                origins=("Oregon", "Willamette Valley"),
                vintage=2025,
                block_ids=("B1",),
                source_lot_ids=(lot_id,),
            ),
        ),
    )


class BottlingPhysicalInventoryTests(unittest.TestCase):
    def test_exact_fill_volume_and_explicit_bottling_loss(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk(volume_l=100.0))

        manifest = bottle_winery_lot(
            ledger=ledger,
            source_lot_id="bulk",
            bottled_lot_id="bottled",
            bottle_count=100,
            bottle_ml=750,
            bottling_loss_l=1.0,
            packaging_assessment=assessment(),
        )

        self.assertAlmostEqual(manifest.filled_volume_l, 75.0)
        self.assertAlmostEqual(manifest.input_volume_l, 76.0)
        self.assertAlmostEqual(manifest.bottling_loss_l, 1.0)
        self.assertAlmostEqual(ledger.available_volume_l("bulk"), 24.0)
        self.assertAlmostEqual(ledger.available_volume_l("bottled"), 75.0)
        self.assertAlmostEqual(ledger.total_recorded_loss_l(), 1.0)
        self.assertEqual(manifest.lot.bottle_count, 100)
        self.assertEqual(manifest.lot.bottle_ml, 750)
        self.assertEqual(manifest.lot.stage, "bottled")

    def test_packaging_assessment_is_required_by_default_and_failure_is_atomic(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk(volume_l=20.0))

        with self.assertRaises(BottlingLotConstraintError):
            bottle_winery_lot(
                ledger=ledger,
                source_lot_id="bulk",
                bottled_lot_id="bottled",
                bottle_count=12,
                bottle_ml=750,
            )

        self.assertAlmostEqual(ledger.available_volume_l("bulk"), 20.0)
        self.assertNotIn("bottled", ledger.lots)
        self.assertEqual(ledger.movements, [])

    def test_insufficient_source_volume_is_atomic(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk(volume_l=5.0))

        with self.assertRaises(BottlingLotConstraintError):
            bottle_winery_lot(
                ledger=ledger,
                source_lot_id="bulk",
                bottled_lot_id="bottled",
                bottle_count=8,
                bottle_ml=750,
                packaging_assessment=assessment(),
            )

        self.assertAlmostEqual(ledger.available_volume_l("bulk"), 5.0)
        self.assertNotIn("bottled", ledger.lots)
        self.assertEqual(ledger.movements, [])

    def test_large_format_volume_is_exact_and_not_inferred_from_name(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk(volume_l=20.0))

        manifest = bottle_winery_lot(
            ledger=ledger,
            source_lot_id="bulk",
            bottled_lot_id="magnums",
            bottle_count=10,
            bottle_ml=1500,
            packaging_assessment=assessment(),
        )

        self.assertAlmostEqual(manifest.filled_volume_l, 15.0)
        self.assertEqual(manifest.lot.bottle_count, 10)
        self.assertEqual(manifest.lot.bottle_ml, 1500)
        self.assertAlmostEqual(ledger.available_volume_l("bulk"), 5.0)

    def test_incomplete_packaging_oxygen_remains_explicit(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk(volume_l=10.0))
        manifest = bottle_winery_lot(
            ledger=ledger,
            source_lot_id="bulk",
            bottled_lot_id="bottled",
            bottle_count=12,
            packaging_assessment=assessment(complete=False),
        )
        self.assertFalse(manifest.packaging_oxygen_assessment_complete)
        self.assertIn("oxygen evidence incomplete", manifest.packaging_warnings)

    def test_packaging_assessment_can_only_be_waived_explicitly(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk(volume_l=10.0))
        manifest = bottle_winery_lot(
            ledger=ledger,
            source_lot_id="bulk",
            bottled_lot_id="bottled",
            bottle_count=12,
            packaging_assessment=None,
            require_packaging_assessment=False,
        )
        self.assertFalse(manifest.packaging_oxygen_assessment_complete)
        self.assertEqual(manifest.tartrate_test_status, "unknown")
        self.assertTrue(any("waived" in warning for warning in manifest.packaging_warnings))

    def test_packaged_lot_cannot_use_generic_transfer_or_blend(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk(volume_l=20.0))
        manifest = bottle_winery_lot(
            ledger=ledger,
            source_lot_id="bulk",
            bottled_lot_id="bottled",
            bottle_count=20,
            packaging_assessment=assessment(),
        )
        with self.assertRaises(WineryProvenanceError):
            ledger.transfer("bottled", new_id="bulk-again", stage="bulk")
        ledger.add(bulk("other", volume_l=5.0))
        with self.assertRaises(WineryProvenanceError):
            ledger.blend([manifest.lot.id, "other"], new_id="bad-blend")

    def test_packaged_dispatch_and_discard_require_whole_bottles(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk(volume_l=20.0))
        bottle_winery_lot(
            ledger=ledger,
            source_lot_id="bulk",
            bottled_lot_id="bottled",
            bottle_count=20,
            packaging_assessment=assessment(),
        )
        with self.assertRaises(WineryProvenanceError):
            ledger.dispatch(
                "bottled", volume_l=0.50, external_reference="half-bottle-dispatch"
            )
        with self.assertRaises(WineryProvenanceError):
            ledger.discard("bottled", volume_l=0.50, reason="impossible partial sealed bottle")
        self.assertAlmostEqual(ledger.available_volume_l("bottled"), 15.0)

    def test_direct_package_metadata_must_match_lot_volume(self):
        with self.assertRaises(WineryProvenanceError):
            WineryLot(
                id="bad",
                stage="bottled",
                volume_l=10.0,
                provenance=(
                    ProvenanceSlice(
                        volume_l=10.0,
                        grape="Pinot Noir",
                        country="United States",
                        origins=("Oregon",),
                        vintage=2025,
                    ),
                ),
                bottle_count=10,
                bottle_ml=750,
            )

    def test_nonfinite_bottling_loss_is_rejected(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk(volume_l=20.0))
        with self.assertRaises(BottlingLotConstraintError):
            bottle_winery_lot(
                ledger=ledger,
                source_lot_id="bulk",
                bottled_lot_id="bottled",
                bottle_count=10,
                bottling_loss_l=float("nan"),
                packaging_assessment=assessment(),
            )


if __name__ == "__main__":
    unittest.main()
