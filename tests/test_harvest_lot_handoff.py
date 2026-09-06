from __future__ import annotations

import unittest
from dataclasses import replace
from types import SimpleNamespace

from sommelier_v2.knowledge.fermentation_process import MustComposition
from sommelier_v2.knowledge.harvest_lot import lot_from_harvest_must
from sommelier_v2.knowledge.harvest_must import HarvestMustProfile
from sommelier_v2.knowledge.winery_provenance import WineryProvenanceError, WineryProvenanceLedger


def block(*, block_id="B1", grape="Pinot Noir"):
    return SimpleNamespace(
        id=block_id,
        grape=grape,
        country="United States",
        region="Oregon",
        appellation="Willamette Valley",
        site_id="site:estate",
    )


def profile(*, block_id="B1", grape="Pinot Noir", volume_l=612.3):
    must = MustComposition(
        volume_l=volume_l,
        sugar_g_l=215.0,
        yan_mg_l=180.0,
        ph=3.45,
        titratable_acidity_g_l=6.2,
        malic_acid_g_l=2.1,
    )
    return HarvestMustProfile(
        must=must,
        source_block_id=block_id,
        source_grape=grape,
        harvested_tonnes=1.0,
        sorting_loss_fraction=0.10,
        usable_tonnes=0.90,
        must_volume_l=volume_l,
        yan_source="measured",
        retained_botrytis_fraction=0.0,
        retained_rot_fraction=0.0,
        fruit_integrity_index=0.95,
        microbial_risk_index=0.05,
        oxidation_risk_index=0.08,
        extraction_potential_index=0.70,
    )


class HarvestLotHandoffTests(unittest.TestCase):
    def test_opening_lot_uses_recovered_must_volume_exactly(self):
        result = lot_from_harvest_must(
            profile(volume_l=612.3), lot_id="must:1", block=block(), vintage_year=2025
        )
        self.assertAlmostEqual(result.volume_l, 612.3)
        self.assertAlmostEqual(result.provenance[0].volume_l, 612.3)
        self.assertEqual(result.stage, "processed_must")

    def test_geographic_and_block_provenance_are_preserved(self):
        result = lot_from_harvest_must(
            profile(), lot_id="must:1", block=block(), vintage_year=2025
        )
        row = result.provenance[0]
        self.assertEqual(row.country, "United States")
        self.assertEqual(row.origins, ("Oregon", "Willamette Valley", "site:estate"))
        self.assertEqual(row.block_ids, ("B1",))
        self.assertEqual(row.vintage, 2025)

    def test_profile_and_must_volume_must_agree(self):
        source = profile()
        corrupted = replace(source, must=replace(source.must, volume_l=600.0))
        with self.assertRaises(WineryProvenanceError):
            lot_from_harvest_must(corrupted, lot_id="bad", block=block(), vintage_year=2025)

    def test_wrong_block_identity_is_rejected(self):
        with self.assertRaises(WineryProvenanceError):
            lot_from_harvest_must(
                profile(block_id="B1"),
                lot_id="bad",
                block=block(block_id="B2"),
                vintage_year=2025,
            )

    def test_wrong_grape_identity_is_rejected(self):
        with self.assertRaises(WineryProvenanceError):
            lot_from_harvest_must(
                profile(grape="Pinot Noir"),
                lot_id="bad",
                block=block(grape="Chardonnay"),
                vintage_year=2025,
            )

    def test_processed_must_can_be_opened_in_conserving_ledger(self):
        ledger = WineryProvenanceLedger()
        lot = ledger.add(
            lot_from_harvest_must(
                profile(volume_l=612.3),
                lot_id="must:1",
                block=block(),
                vintage_year=2025,
            )
        )
        self.assertAlmostEqual(ledger.available_volume_l(lot.id), 612.3)
        ferment = ledger.transfer(
            lot.id,
            new_id="ferment:1",
            stage="fermentation",
            input_volume_l=612.3,
            output_volume_l=600.0,
        )
        self.assertAlmostEqual(ledger.available_volume_l(lot.id), 0.0)
        self.assertAlmostEqual(ferment.volume_l, 600.0)
        self.assertAlmostEqual(ledger.total_recorded_loss_l(), 12.3)

    def test_invalid_vintage_is_rejected(self):
        with self.assertRaises(WineryProvenanceError):
            lot_from_harvest_must(profile(), lot_id="bad", block=block(), vintage_year=1200)


if __name__ == "__main__":
    unittest.main()
