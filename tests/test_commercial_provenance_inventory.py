from __future__ import annotations

import unittest

from sommelier_v2.commercial_provenance import (
    CommercialProvenanceError,
    dispatch_winery_lot_to_inventory,
    inventory_provenance_components,
    provenance_fingerprint,
)
from sommelier_v2.domain import BeverageProgram, InventoryLot, WineRecord, WineStyle
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


def winery_lot(
    lot_id: str,
    *,
    volume_l: float = 10.0,
    grape: str = "Cabernet Sauvignon",
    block_id: str = "B1",
    stage: str = "bottled",
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


class CommercialProvenanceInventoryTests(unittest.TestCase):
    def test_successful_dispatch_consumes_winery_volume_without_recording_loss(self):
        ledger = WineryProvenanceLedger()
        ledger.add(winery_lot("bottled:1", volume_l=10.0))
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
        self.assertAlmostEqual(ledger.available_volume_l("bottled:1"), 5.5)
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
        ledger.add(winery_lot("bottled:1"))
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

        self.assertAlmostEqual(ledger.available_volume_l("bottled:1"), 10.0)
        self.assertEqual(ledger.movements, [])
        self.assertEqual(program.inventory, {})
        self.assertAlmostEqual(program.cash, 10.0)

    def test_insufficient_cellar_capacity_does_not_consume_source(self):
        ledger = WineryProvenanceLedger()
        ledger.add(winery_lot("bottled:1"))
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

        self.assertAlmostEqual(ledger.available_volume_l("bottled:1"), 10.0)
        self.assertEqual(ledger.movements, [])
        self.assertEqual(program.inventory, {})

    def test_duplicate_restaurant_lot_id_does_not_consume_source(self):
        ledger = WineryProvenanceLedger()
        ledger.add(winery_lot("bottled:1"))
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

        self.assertAlmostEqual(ledger.available_volume_l("bottled:1"), 10.0)
        self.assertEqual(ledger.movements, [])
        self.assertEqual(program.inventory["restaurant:1"].wine.id, "existing")

    def test_insufficient_winery_volume_does_not_mutate_restaurant(self):
        ledger = WineryProvenanceLedger()
        ledger.add(winery_lot("bottled:1", volume_l=1.0))
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

        self.assertAlmostEqual(ledger.available_volume_l("bottled:1"), 1.0)
        self.assertEqual(program.inventory, {})
        self.assertAlmostEqual(program.cash, 1000.0)

    def test_blend_proportions_survive_commercial_handoff(self):
        ledger = WineryProvenanceLedger()
        ledger.add(winery_lot("cab", volume_l=10.0, grape="Cabernet Sauvignon", block_id="CAB"))
        ledger.add(winery_lot("merlot", volume_l=10.0, grape="Merlot", block_id="MER"))
        blend = ledger.blend(
            ["cab", "merlot"],
            new_id="blend:bottled",
            draws_l=[8.0, 2.0],
            stage="bottled",
        )
        program = BeverageProgram(name="Restaurant", cash=1000.0)

        result = dispatch_winery_lot_to_inventory(
            ledger=ledger,
            program=program,
            source_winery_lot_id=blend.id,
            inventory_lot_id="restaurant:blend",
            wine=wine(),
            bottles=4,
            unit_cost=25.0,
            dispatch_reference="dispatch:blend",
        )

        pct = {component.grape: component.volume_pct for component in result.inventory_lot.provenance_components}
        self.assertAlmostEqual(pct["Cabernet Sauvignon"], 80.0)
        self.assertAlmostEqual(pct["Merlot"], 20.0)

    def test_fingerprint_is_deterministic_and_lot_specific(self):
        first = winery_lot("lot:a")
        second = winery_lot("lot:b")
        self.assertEqual(provenance_fingerprint(first), provenance_fingerprint(first))
        self.assertNotEqual(provenance_fingerprint(first), provenance_fingerprint(second))
        components = inventory_provenance_components(first)
        self.assertEqual(components[0].source_lot_ids, ("lot:a",))

    def test_non_bottled_source_is_rejected_by_default(self):
        ledger = WineryProvenanceLedger()
        ledger.add(winery_lot("bulk:1", stage="elevage"))
        program = BeverageProgram(name="Restaurant", cash=1000.0)
        with self.assertRaises(CommercialProvenanceError):
            dispatch_winery_lot_to_inventory(
                ledger=ledger,
                program=program,
                source_winery_lot_id="bulk:1",
                inventory_lot_id="restaurant:1",
                wine=wine(),
                bottles=1,
                unit_cost=20.0,
                dispatch_reference="dispatch:not-bottled",
            )
        self.assertAlmostEqual(ledger.available_volume_l("bulk:1"), 10.0)

    def test_bool_bottle_count_is_not_accepted_as_integer(self):
        ledger = WineryProvenanceLedger()
        ledger.add(winery_lot("bottled:1"))
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
