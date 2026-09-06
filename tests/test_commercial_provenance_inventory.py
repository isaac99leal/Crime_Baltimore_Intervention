from __future__ import annotations

import unittest

from sommelier_v2.commercial_provenance import (
    CommercialProvenanceError,
    dispatch_winery_lot_to_inventory,
    inventory_provenance_components,
    provenance_fingerprint,
)
from sommelier_v2.domain import BeverageProgram, InventoryLot, WineRecord, WineStyle
from sommelier_v2.knowledge.bottling_lot import bottle_winery_lot
from sommelier_v2.knowledge.packaging import PackagingAssessment
from sommelier_v2.knowledge.winery_provenance import (
    ProvenanceSlice,
    WineryLot,
    WineryProvenanceLedger,
)


def wine(*, wine_id: str = "wine:1") -> WineRecord:
    return WineRecord(
        id=wine_id,
        producer="Test Estate",
        label="Estate Red",
        country="United States",
        region="California",
        vintage=2025,
        style=WineStyle.RED,
        grapes=("Cabernet Sauvignon", "Merlot"),
    )


def packaging() -> PackagingAssessment:
    return PackagingAssessment(
        prebottling_oxygen_risk_index=0.05,
        closure_oxygen_exposure_prior=0.20,
        oxygen_assessment_complete=True,
        ageing_oxygen_modifier=1.10,
        free_so2_cost_guide_upper_mg_l=1.2,
        molecular_so2_before_packaging_mg_l=0.55,
        tartrate_test_status="tested_stable",
        tartrate_physical_instability_risk=0.0,
        warnings=(),
        evidence_record_ids=(),
    )


def bulk_lot(
    lot_id: str,
    *,
    volume_l: float = 10.0,
    grape: str = "Cabernet Sauvignon",
    block_id: str = "B1",
    stage: str = "finished_wine",
) -> WineryLot:
    return WineryLot(
        id=lot_id,
        stage=stage,
        volume_l=volume_l,
        provenance=(
            ProvenanceSlice(
                volume_l=volume_l,
                grape=grape,
                country="United States",
                origins=("California", "Napa Valley"),
                vintage=2025,
                block_ids=(block_id,),
                source_lot_ids=(lot_id,),
            ),
        ),
    )


def packaged_lot(
    lot_id: str,
    *,
    bottle_count: int = 10,
    bottle_ml: int = 750,
    grape: str = "Cabernet Sauvignon",
    block_id: str = "B1",
    stage: str = "bottled",
) -> WineryLot:
    volume_l = bottle_count * bottle_ml / 1000.0
    return WineryLot(
        id=lot_id,
        stage=stage,
        volume_l=volume_l,
        provenance=(
            ProvenanceSlice(
                volume_l=volume_l,
                grape=grape,
                country="United States",
                origins=("California", "Napa Valley"),
                vintage=2025,
                block_ids=(block_id,),
                source_lot_ids=(lot_id,),
            ),
        ),
        bottle_count=bottle_count,
        bottle_ml=bottle_ml,
    )


class CommercialProvenanceInventoryTests(unittest.TestCase):
    def test_successful_dispatch_consumes_whole_source_bottles_without_recording_loss(self):
        ledger = WineryProvenanceLedger()
        ledger.add(packaged_lot("bottled:1", bottle_count=10))
        program = BeverageProgram(name="Restaurant", cash=1000.0, cellar_capacity_bottles=100)

        result = dispatch_winery_lot_to_inventory(
            ledger=ledger,
            program=program,
            source_winery_lot_id="bottled:1",
            inventory_lot_id="restaurant:1",
            wine=wine(),
            bottles=6,
            unit_cost=20.0,
            dispatch_reference="dispatch:001",
            supplier_id="estate-direct",
        )

        self.assertAlmostEqual(result.dispatched_volume_l, 4.5)
        self.assertAlmostEqual(ledger.available_volume_l("bottled:1"), 3.0)
        self.assertAlmostEqual(ledger.total_dispatched_volume_l(), 4.5)
        self.assertAlmostEqual(ledger.total_recorded_loss_l(), 0.0)
        self.assertEqual(result.movement.operation, "dispatch")
        self.assertEqual(result.movement.external_reference, "dispatch:001")
        self.assertAlmostEqual(result.movement.loss_volume_l, 0.0)
        self.assertEqual(program.inventory["restaurant:1"].sealed_bottles, 6)
        self.assertEqual(program.inventory["restaurant:1"].source_winery_lot_id, "bottled:1")
        self.assertEqual(program.inventory["restaurant:1"].source_dispatch_reference, "dispatch:001")
        self.assertEqual(program.inventory["restaurant:1"].supplier_id, "estate-direct")
        self.assertAlmostEqual(program.cash, 880.0)
        self.assertEqual(len(result.provenance_fingerprint), 64)
        self.assertAlmostEqual(
            sum(c.volume_pct for c in result.inventory_lot.provenance_components),
            100.0,
        )

    def test_insufficient_restaurant_cash_does_not_consume_source(self):
        ledger = WineryProvenanceLedger()
        ledger.add(packaged_lot("bottled:1"))
        program = BeverageProgram(name="Restaurant", cash=10.0)

        with self.assertRaises(ValueError):
            dispatch_winery_lot_to_inventory(
                ledger=ledger,
                program=program,
                source_winery_lot_id="bottled:1",
                inventory_lot_id="restaurant:1",
                wine=wine(),
                bottles=2,
                unit_cost=20.0,
                dispatch_reference="dispatch:cash-fail",
            )

        self.assertAlmostEqual(ledger.available_volume_l("bottled:1"), 7.5)
        self.assertEqual(ledger.movements, [])
        self.assertEqual(program.inventory, {})
        self.assertAlmostEqual(program.cash, 10.0)

    def test_insufficient_cellar_capacity_does_not_consume_source(self):
        ledger = WineryProvenanceLedger()
        ledger.add(packaged_lot("bottled:1"))
        program = BeverageProgram(name="Restaurant", cash=1000.0, cellar_capacity_bottles=1)

        with self.assertRaises(ValueError):
            dispatch_winery_lot_to_inventory(
                ledger=ledger,
                program=program,
                source_winery_lot_id="bottled:1",
                inventory_lot_id="restaurant:1",
                wine=wine(),
                bottles=2,
                unit_cost=20.0,
                dispatch_reference="dispatch:capacity-fail",
            )

        self.assertAlmostEqual(ledger.available_volume_l("bottled:1"), 7.5)
        self.assertEqual(ledger.movements, [])
        self.assertEqual(program.inventory, {})

    def test_duplicate_restaurant_lot_id_does_not_consume_source(self):
        ledger = WineryProvenanceLedger()
        ledger.add(packaged_lot("bottled:1"))
        program = BeverageProgram(name="Restaurant", cash=1000.0)
        program.inventory["restaurant:1"] = InventoryLot(
            lot_id="restaurant:1",
            wine=wine(wine_id="existing"),
            sealed_bottles=1,
            unit_cost=10.0,
            received_day=program.day,
        )

        with self.assertRaises(ValueError):
            dispatch_winery_lot_to_inventory(
                ledger=ledger,
                program=program,
                source_winery_lot_id="bottled:1",
                inventory_lot_id="restaurant:1",
                wine=wine(),
                bottles=2,
                unit_cost=20.0,
                dispatch_reference="dispatch:duplicate-fail",
            )

        self.assertAlmostEqual(ledger.available_volume_l("bottled:1"), 7.5)
        self.assertEqual(ledger.movements, [])
        self.assertEqual(program.inventory["restaurant:1"].wine.id, "existing")

    def test_insufficient_winery_bottle_count_does_not_mutate_restaurant(self):
        ledger = WineryProvenanceLedger()
        ledger.add(packaged_lot("bottled:1", bottle_count=1))
        program = BeverageProgram(name="Restaurant", cash=1000.0)

        with self.assertRaises(CommercialProvenanceError):
            dispatch_winery_lot_to_inventory(
                ledger=ledger,
                program=program,
                source_winery_lot_id="bottled:1",
                inventory_lot_id="restaurant:1",
                wine=wine(),
                bottles=2,
                unit_cost=20.0,
                dispatch_reference="dispatch:source-fail",
            )

        self.assertAlmostEqual(ledger.available_volume_l("bottled:1"), 0.75)
        self.assertEqual(program.inventory, {})
        self.assertAlmostEqual(program.cash, 1000.0)

    def test_blend_proportions_survive_bottling_and_commercial_handoff(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk_lot("cab", volume_l=10.0, grape="Cabernet Sauvignon", block_id="CAB"))
        ledger.add(bulk_lot("merlot", volume_l=10.0, grape="Merlot", block_id="MER"))
        blend = ledger.blend(
            ["cab", "merlot"],
            new_id="blend:bulk",
            draws_l=[8.0, 2.0],
            stage="finished_wine",
        )
        bottled = bottle_winery_lot(
            ledger=ledger,
            source_lot_id=blend.id,
            bottled_lot_id="blend:bottled",
            bottle_count=12,
            bottle_ml=750,
            packaging_assessment=packaging(),
        )
        program = BeverageProgram(name="Restaurant", cash=1000.0)

        result = dispatch_winery_lot_to_inventory(
            ledger=ledger,
            program=program,
            source_winery_lot_id=bottled.lot.id,
            inventory_lot_id="restaurant:blend",
            wine=wine(),
            bottles=4,
            unit_cost=25.0,
            dispatch_reference="dispatch:blend",
        )

        pct = {component.grape: component.volume_pct for component in result.inventory_lot.provenance_components}
        self.assertAlmostEqual(pct["Cabernet Sauvignon"], 80.0)
        self.assertAlmostEqual(pct["Merlot"], 20.0)

    def test_fingerprint_is_deterministic_lot_and_format_specific(self):
        first = packaged_lot("lot:a", bottle_count=10, bottle_ml=750)
        same = packaged_lot("lot:a", bottle_count=10, bottle_ml=750)
        different_lot = packaged_lot("lot:b", bottle_count=10, bottle_ml=750)
        different_format = packaged_lot("lot:a", bottle_count=5, bottle_ml=1500)
        self.assertEqual(provenance_fingerprint(first), provenance_fingerprint(same))
        self.assertNotEqual(provenance_fingerprint(first), provenance_fingerprint(different_lot))
        self.assertNotEqual(provenance_fingerprint(first), provenance_fingerprint(different_format))
        components = inventory_provenance_components(first)
        self.assertEqual(components[0].source_lot_ids, ("lot:a",))

    def test_non_bottled_stage_is_rejected_by_default_even_with_package_metadata(self):
        ledger = WineryProvenanceLedger()
        ledger.add(packaged_lot("legacy:1", stage="elevage"))
        program = BeverageProgram(name="Restaurant", cash=1000.0)
        with self.assertRaises(CommercialProvenanceError):
            dispatch_winery_lot_to_inventory(
                ledger=ledger,
                program=program,
                source_winery_lot_id="legacy:1",
                inventory_lot_id="restaurant:1",
                wine=wine(),
                bottles=1,
                unit_cost=20.0,
                dispatch_reference="dispatch:not-bottled",
            )
        self.assertAlmostEqual(ledger.available_volume_l("legacy:1"), 7.5)

    def test_bottled_stage_without_package_metadata_cannot_create_sealed_inventory(self):
        ledger = WineryProvenanceLedger()
        ledger.add(bulk_lot("fake:bottled", stage="bottled"))
        program = BeverageProgram(name="Restaurant", cash=1000.0)
        with self.assertRaises(CommercialProvenanceError):
            dispatch_winery_lot_to_inventory(
                ledger=ledger,
                program=program,
                source_winery_lot_id="fake:bottled",
                inventory_lot_id="restaurant:1",
                wine=wine(),
                bottles=1,
                unit_cost=20.0,
                dispatch_reference="dispatch:no-package-metadata",
            )

    def test_bottle_format_cannot_change_during_dispatch(self):
        ledger = WineryProvenanceLedger()
        ledger.add(packaged_lot("bottled:750", bottle_count=10, bottle_ml=750))
        program = BeverageProgram(name="Restaurant", cash=1000.0)
        with self.assertRaises(CommercialProvenanceError):
            dispatch_winery_lot_to_inventory(
                ledger=ledger,
                program=program,
                source_winery_lot_id="bottled:750",
                inventory_lot_id="restaurant:magnum",
                wine=wine(),
                bottles=2,
                bottle_ml=1500,
                unit_cost=20.0,
                dispatch_reference="dispatch:format-change",
            )
        self.assertAlmostEqual(ledger.available_volume_l("bottled:750"), 7.5)

    def test_bool_bottle_count_is_not_accepted_as_integer(self):
        ledger = WineryProvenanceLedger()
        ledger.add(packaged_lot("bottled:1"))
        program = BeverageProgram(name="Restaurant", cash=1000.0)
        with self.assertRaises(CommercialProvenanceError):
            dispatch_winery_lot_to_inventory(
                ledger=ledger,
                program=program,
                source_winery_lot_id="bottled:1",
                inventory_lot_id="restaurant:1",
                wine=wine(),
                bottles=True,
                unit_cost=20.0,
                dispatch_reference="dispatch:bool",
            )


if __name__ == "__main__":
    unittest.main()
