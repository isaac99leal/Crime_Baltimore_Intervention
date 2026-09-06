from __future__ import annotations

from dataclasses import replace
import unittest

from sommelier_v2.commercial_provenance import (
    CommercialProvenanceError,
    dispatch_bottled_manifest_to_inventory,
    dispatch_winery_lot_to_inventory,
    packaging_snapshot_from_assessment,
)
from sommelier_v2.domain import BeverageProgram, InventoryLot, WineRecord, WineStyle
from sommelier_v2.knowledge.bottle_lifecycle import (
    BottleAgingPlan,
    BottleLifecycleConstraintError,
    age_inventory_lot,
)
from sommelier_v2.knowledge.bottling_lot import bottle_winery_lot
from sommelier_v2.knowledge.packaging import PackagingAssessment
from sommelier_v2.knowledge.schema import AgingArchetype
from sommelier_v2.knowledge.winery_provenance import (
    ProvenanceSlice,
    WineryLot,
    WineryProvenanceLedger,
)


def assessment(*, complete: bool = True, unstable: bool = False) -> PackagingAssessment:
    return PackagingAssessment(
        prebottling_oxygen_risk_index=0.10 if complete else 0.10,
        closure_oxygen_exposure_prior=0.20 if complete else None,
        oxygen_assessment_complete=complete,
        ageing_oxygen_modifier=1.195 if complete else 1.085,
        free_so2_cost_guide_upper_mg_l=1.6,
        molecular_so2_before_packaging_mg_l=0.75,
        tartrate_test_status="tested_unstable" if unstable else "tested_stable",
        tartrate_physical_instability_risk=1.0 if unstable else 0.0,
        warnings=("source packaging warning",),
        evidence_record_ids=("chem-prebottling-dissolved-oxygen", "chem-tartrate-stability"),
    )


def bulk_lot(lot_id: str = "bulk:1", *, volume_l: float = 100.0) -> WineryLot:
    return WineryLot(
        id=lot_id,
        stage="finished_bulk",
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


def wine() -> WineRecord:
    return WineRecord(
        id="wine:1",
        producer="Test Estate",
        label="Estate Pinot Noir",
        country="United States",
        region="Oregon",
        appellation="Willamette Valley",
        vintage=2025,
        style=WineStyle.RED,
        grapes=("Pinot Noir",),
    )


def archetype() -> AgingArchetype:
    return AgingArchetype(
        id="inventory-test",
        name="Inventory Test",
        maturity_years=4.0,
        peak_years=8.0,
        decline_half_life_years=8.0,
        primary_half_life_years=6.0,
        floral_half_life_years=4.0,
        tertiary_onset_years=4.0,
        tertiary_peak_years=10.0,
        tannin_softening_half_life_years=8.0,
        freshness_half_life_years=7.0,
        oxidation_onset_years=10.0,
        oxidation_rate=0.2,
        complexity_peak_years=9.0,
        sediment_onset_years=7.0,
        color_shift_rate=0.08,
    )


class CommercialPackagingSnapshotTests(unittest.TestCase):
    def test_snapshot_translation_preserves_packaging_evidence(self):
        source = assessment(complete=True, unstable=True)
        snapshot = packaging_snapshot_from_assessment(source)
        self.assertTrue(snapshot.oxygen_assessment_complete)
        self.assertAlmostEqual(snapshot.ageing_oxygen_modifier, source.ageing_oxygen_modifier)
        self.assertAlmostEqual(
            snapshot.molecular_so2_before_packaging_mg_l,
            source.molecular_so2_before_packaging_mg_l,
        )
        self.assertEqual(snapshot.tartrate_test_status, "tested_unstable")
        self.assertEqual(snapshot.tartrate_physical_instability_risk, 1.0)
        self.assertEqual(snapshot.warnings, source.warnings)
        self.assertEqual(snapshot.evidence_record_ids, source.evidence_record_ids)

    def test_manifest_dispatch_carries_snapshot_into_restaurant_inventory(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk_lot())
        package = assessment(complete=True)
        manifest = bottle_winery_lot(
            ledger=ledger,
            source_lot_id="bulk:1",
            bottled_lot_id="bottled:1",
            bottle_count=100,
            bottle_ml=750,
            bottling_loss_l=1.0,
            packaging_assessment=package,
        )
        program = BeverageProgram(name="Restaurant", cash=5000.0)

        result = dispatch_bottled_manifest_to_inventory(
            ledger=ledger,
            program=program,
            manifest=manifest,
            inventory_lot_id="restaurant:1",
            wine=wine(),
            bottles=12,
            unit_cost=30.0,
            dispatch_reference="dispatch:1",
        )

        snapshot = result.inventory_lot.packaging_snapshot
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertTrue(snapshot.oxygen_assessment_complete)
        self.assertAlmostEqual(snapshot.ageing_oxygen_modifier, package.ageing_oxygen_modifier)
        self.assertEqual(snapshot.evidence_record_ids, package.evidence_record_ids)
        self.assertEqual(result.inventory_lot.bottle_ml, 750)
        self.assertAlmostEqual(ledger.available_volume_l("bottled:1"), 66.0)

    def test_inventory_aging_uses_stored_packaging_modifier(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk_lot())
        package = assessment(complete=True, unstable=True)
        manifest = bottle_winery_lot(
            ledger=ledger,
            source_lot_id="bulk:1",
            bottled_lot_id="bottled:1",
            bottle_count=100,
            packaging_assessment=package,
        )
        program = BeverageProgram(name="Restaurant", cash=5000.0)
        dispatched = dispatch_bottled_manifest_to_inventory(
            ledger=ledger,
            program=program,
            manifest=manifest,
            inventory_lot_id="restaurant:1",
            wine=wine(),
            bottles=6,
            unit_cost=30.0,
            dispatch_reference="dispatch:aging",
        )

        aged = age_inventory_lot(
            archetype(),
            dispatched.inventory_lot,
            BottleAgingPlan(age_years=8.0),
        )

        self.assertAlmostEqual(aged.packaging_oxygen_modifier, package.ageing_oxygen_modifier)
        self.assertTrue(aged.packaging_oxygen_complete)
        self.assertFalse(aged.conditional_on_incomplete_oxygen)
        self.assertTrue(any("tartrate-unstable" in warning for warning in aged.warnings))
        self.assertTrue(any("source packaging warning" in warning for warning in aged.warnings))

    def test_incomplete_packaging_snapshot_requires_explicit_conditional_mode(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk_lot())
        manifest = bottle_winery_lot(
            ledger=ledger,
            source_lot_id="bulk:1",
            bottled_lot_id="bottled:1",
            bottle_count=100,
            packaging_assessment=assessment(complete=False),
        )
        program = BeverageProgram(name="Restaurant", cash=5000.0)
        dispatched = dispatch_bottled_manifest_to_inventory(
            ledger=ledger,
            program=program,
            manifest=manifest,
            inventory_lot_id="restaurant:1",
            wine=wine(),
            bottles=6,
            unit_cost=30.0,
            dispatch_reference="dispatch:conditional",
        )

        with self.assertRaises(BottleLifecycleConstraintError):
            age_inventory_lot(
                archetype(),
                dispatched.inventory_lot,
                BottleAgingPlan(age_years=5.0),
            )

        aged = age_inventory_lot(
            archetype(),
            dispatched.inventory_lot,
            BottleAgingPlan(age_years=5.0, require_complete_packaging_oxygen=False),
        )
        self.assertTrue(aged.conditional_on_incomplete_oxygen)
        self.assertTrue(any("conditional" in warning for warning in aged.warnings))

    def test_assessment_waiver_remains_unknown_after_dispatch(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk_lot())
        manifest = bottle_winery_lot(
            ledger=ledger,
            source_lot_id="bulk:1",
            bottled_lot_id="bottled:1",
            bottle_count=100,
            packaging_assessment=None,
            require_packaging_assessment=False,
        )
        program = BeverageProgram(name="Restaurant", cash=5000.0)
        dispatched = dispatch_bottled_manifest_to_inventory(
            ledger=ledger,
            program=program,
            manifest=manifest,
            inventory_lot_id="restaurant:1",
            wine=wine(),
            bottles=6,
            unit_cost=30.0,
            dispatch_reference="dispatch:waived",
        )
        self.assertIsNone(dispatched.inventory_lot.packaging_snapshot)
        with self.assertRaises(BottleLifecycleConstraintError):
            age_inventory_lot(
                archetype(),
                dispatched.inventory_lot,
                BottleAgingPlan(age_years=5.0, require_complete_packaging_oxygen=False),
            )

    def test_legacy_dispatch_does_not_fabricate_packaging_snapshot(self):
        ledger = WineryProvenanceLedger()
        ledger.add(
            WineryLot(
                id="legacy:bottled",
                stage="bottled",
                volume_l=7.5,
                bottle_count=10,
                bottle_ml=750,
                provenance=(
                    ProvenanceSlice(
                        volume_l=7.5,
                        grape="Pinot Noir",
                        country="United States",
                        origins=("Oregon",),
                        vintage=2024,
                        source_lot_ids=("legacy:bottled",),
                    ),
                ),
            )
        )
        program = BeverageProgram(name="Restaurant", cash=5000.0)
        result = dispatch_winery_lot_to_inventory(
            ledger=ledger,
            program=program,
            source_winery_lot_id="legacy:bottled",
            inventory_lot_id="restaurant:legacy",
            wine=wine(),
            bottles=2,
            unit_cost=20.0,
            dispatch_reference="dispatch:legacy",
        )
        self.assertIsNone(result.inventory_lot.packaging_snapshot)

    def test_stale_manifest_fails_before_custody_mutates(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk_lot())
        manifest = bottle_winery_lot(
            ledger=ledger,
            source_lot_id="bulk:1",
            bottled_lot_id="bottled:1",
            bottle_count=100,
            packaging_assessment=assessment(),
        )
        stale = replace(manifest, bottle_ml=1500)
        program = BeverageProgram(name="Restaurant", cash=5000.0)
        before = ledger.available_volume_l("bottled:1")

        with self.assertRaises(CommercialProvenanceError):
            dispatch_bottled_manifest_to_inventory(
                ledger=ledger,
                program=program,
                manifest=stale,
                inventory_lot_id="restaurant:1",
                wine=wine(),
                bottles=2,
                unit_cost=30.0,
                dispatch_reference="dispatch:stale",
            )

        self.assertAlmostEqual(ledger.available_volume_l("bottled:1"), before)
        self.assertEqual(program.inventory, {})
        self.assertAlmostEqual(program.cash, 5000.0)

    def test_inventory_aging_does_not_infer_from_physical_bottle_size(self):
        item = InventoryLot(
            lot_id="restaurant:no-snapshot",
            wine=wine(),
            sealed_bottles=1,
            unit_cost=20.0,
            received_day=1,
            bottle_ml=1500,
            glass_ml=150,
        )
        with self.assertRaises(BottleLifecycleConstraintError):
            age_inventory_lot(
                archetype(),
                item,
                BottleAgingPlan(
                    age_years=5.0,
                    bottle_size_modifier=1.5,
                    require_complete_packaging_oxygen=False,
                ),
            )


if __name__ == "__main__":
    unittest.main()
