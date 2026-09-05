from __future__ import annotations

import unittest
from types import SimpleNamespace

from sommelier_v2.domain import WineRecord, WineStyle
from sommelier_v2.knowledge import (
    FinishedWineAssembler,
    LabelClaims,
    WineryLot,
    WineryProvenanceError,
    WineryProvenanceLedger,
)


def block(block_id, grape, appellation, *, area=1.0):
    return SimpleNamespace(
        id=block_id,
        grape=grape,
        area_ha=area,
        country="United States",
        region="California",
        appellation=appellation,
        site_id=None,
    )


def outcome(grape, *, yield_hl_ha=50.0, harvestable=True):
    return SimpleNamespace(
        grape=grape,
        yield_hl_ha=yield_hl_ha,
        harvestable=harvestable,
    )


class WineryProvenanceTests(unittest.TestCase):
    def test_vineyard_to_ferment_to_elevage_preserves_provenance(self):
        harvest = WineryLot.from_vineyard(
            lot_id="harvest:napa",
            block=block("B1", "Cabernet Sauvignon", "Napa Valley"),
            outcome=outcome("Cabernet Sauvignon"),
            vintage_year=2025,
        )
        self.assertAlmostEqual(harvest.volume_l, 5000.0)
        ferment = harvest.process(
            new_id="ferment:napa", stage="fermentation", output_volume_l=4800
        )
        elevage = ferment.process(
            new_id="elevage:napa", stage="elevage", output_volume_l=4500
        )
        components = elevage.to_blend_components()
        self.assertEqual(len(components), 1)
        self.assertAlmostEqual(components[0].volume_pct, 100.0)
        self.assertEqual(components[0].origins, ("California", "Napa Valley"))
        self.assertIn("B1", elevage.provenance[0].block_ids)

    def test_blend_draws_generate_finished_wine_ledger_automatically(self):
        ledger = WineryProvenanceLedger()
        napa = ledger.add(
            WineryLot.from_vineyard(
                lot_id="napa",
                block=block("B1", "Cabernet Sauvignon", "Napa Valley"),
                outcome=outcome("Cabernet Sauvignon"),
                vintage_year=2025,
            )
        )
        california = ledger.add(
            WineryLot.from_vineyard(
                lot_id="ca",
                block=block("B2", "Merlot", None),
                outcome=outcome("Merlot"),
                vintage_year=2025,
            )
        )
        blend = ledger.blend(
            ["napa", "ca"], new_id="final-blend", draws_l=[850, 150]
        )
        components = blend.to_blend_components()
        self.assertAlmostEqual(sum(c.volume_pct for c in components), 100.0)
        self.assertAlmostEqual(
            next(c.volume_pct for c in components if c.grape == "Cabernet Sauvignon"),
            85.0,
        )

        prototype = WineRecord(
            id="wine:1",
            producer="Test Estate",
            label="Estate Cabernet",
            country="United States",
            region="California",
            style=WineStyle.RED,
        )
        claims = LabelClaims(
            jurisdiction="US",
            origin_names=("Napa Valley",),
            origin_type="AVA",
            variety_names=("Cabernet Sauvignon",),
            vintage_years=(2025,),
            fully_finished_in_required_area=True,
        )
        wine = blend.assemble_finished_wine(
            prototype, claims=claims, assembler=FinishedWineAssembler()
        )
        self.assertEqual(wine.appellation, "Napa Valley")
        self.assertEqual(wine.vintage, 2025)
        self.assertEqual(wine.grapes, ("Cabernet Sauvignon", "Merlot"))
        self.assertAlmostEqual(
            sum(c.volume_pct for c in wine.provenance_components), 100.0
        )

    def test_processing_and_blending_cannot_create_volume(self):
        lot = WineryLot.from_vineyard(
            lot_id="lot",
            block=block("B1", "Cabernet Sauvignon", "Napa Valley"),
            outcome=outcome("Cabernet Sauvignon"),
            vintage_year=2025,
        )
        with self.assertRaises(WineryProvenanceError):
            lot.process(new_id="bad", stage="fermentation", output_volume_l=6000)
        with self.assertRaises(WineryProvenanceError):
            WineryLot.blend(lot_id="bad-blend", lots=[lot], draws_l=[6000])

    def test_unharvestable_block_cannot_enter_winery_ledger(self):
        with self.assertRaises(WineryProvenanceError):
            WineryLot.from_vineyard(
                lot_id="bad",
                block=block("B1", "Cabernet Sauvignon", "Napa Valley"),
                outcome=outcome("Cabernet Sauvignon", harvestable=False),
                vintage_year=2025,
            )


if __name__ == "__main__":
    unittest.main()
