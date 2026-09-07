from __future__ import annotations

import unittest
from types import SimpleNamespace

from sommelier_v2.knowledge.blend_chemistry import BlendChemistryComponent
from sommelier_v2.knowledge.winery_blend_chemistry import (
    WineryBlendChemistryConstraintError,
    blend_winery_lots_with_chemistry,
)
from sommelier_v2.knowledge.winery_provenance import (
    WineryLot,
    WineryProvenanceError,
    WineryProvenanceLedger,
)


def _block(block_id: str, grape: str):
    return SimpleNamespace(
        id=block_id,
        grape=grape,
        area_ha=1.0,
        country="United States",
        region="California",
        appellation="Napa Valley",
        site_id=None,
    )


def _outcome(grape: str):
    return SimpleNamespace(grape=grape, yield_hl_ha=10.0, harvestable=True)


def _lot(lot_id: str, grape: str, volume_l: float = 1000.0) -> WineryLot:
    return WineryLot.from_vineyard(
        lot_id=lot_id,
        block=_block(f"block:{lot_id}", grape),
        outcome=_outcome(grape),
        vintage_year=2025,
        recovered_volume_l=volume_l,
    )


def _chem(source_id: str, draw_l: float, ethanol_pct: float) -> BlendChemistryComponent:
    return BlendChemistryComponent(
        source_id=source_id,
        draw_l=draw_l,
        ethanol_pct=ethanol_pct,
        residual_sugar_g_l=2.0,
        malic_acid_g_l=1.5,
        lactic_acid_g_l=0.5,
        tartaric_acid_g_l=3.0,
        volatile_acidity_g_l=0.5,
        total_so2_mg_l=80.0,
        dissolved_oxygen_mg_l=1.0,
    )


class WineryBlendChemistryBridgeTests(unittest.TestCase):
    def ledger(self) -> WineryProvenanceLedger:
        ledger = WineryProvenanceLedger()
        ledger.add(_lot("cab", "Cabernet Sauvignon"))
        ledger.add(_lot("merlot", "Merlot"))
        return ledger

    def test_success_uses_exact_same_sources_and_liters_for_both_ledgers(self) -> None:
        ledger = self.ledger()
        # Chemistry order is deliberately reversed; physical order remains authoritative.
        result = blend_winery_lots_with_chemistry(
            ledger,
            ["cab", "merlot"],
            [_chem("merlot", 50.0, 14.0), _chem("cab", 100.0, 12.0)],
            new_id="blend",
            draws_l=[100.0, 50.0],
            operation_oxygen_delta_mg=0.0,
        )

        self.assertEqual(result.chemistry.source_ids, ("cab", "merlot"))
        self.assertEqual(result.movement.source_lot_ids, ("cab", "merlot"))
        self.assertEqual(result.movement.source_draws_l, (100.0, 50.0))
        self.assertEqual(result.chemistry.volume_l, 150.0)
        self.assertEqual(result.movement.output_volume_l, 150.0)
        self.assertEqual(result.lot.volume_l, 150.0)
        self.assertAlmostEqual(result.chemistry.ethanol_pct or 0.0, 12.0 * 2 / 3 + 14.0 / 3)
        self.assertEqual(ledger.available_volume_l("cab"), 900.0)
        self.assertEqual(ledger.available_volume_l("merlot"), 950.0)

    def test_chemistry_draw_mismatch_fails_before_any_physical_mutation(self) -> None:
        ledger = self.ledger()
        with self.assertRaises(WineryBlendChemistryConstraintError):
            blend_winery_lots_with_chemistry(
                ledger,
                ["cab", "merlot"],
                [_chem("cab", 99.0, 12.0), _chem("merlot", 50.0, 14.0)],
                new_id="bad",
                draws_l=[100.0, 50.0],
                operation_oxygen_delta_mg=0.0,
            )
        self.assertEqual(ledger.available_volume_l("cab"), 1000.0)
        self.assertEqual(ledger.available_volume_l("merlot"), 1000.0)
        self.assertEqual(ledger.movements, [])
        self.assertNotIn("bad", ledger.lots)

    def test_chemistry_source_set_mismatch_fails_before_mutation(self) -> None:
        ledger = self.ledger()
        with self.assertRaises(WineryBlendChemistryConstraintError):
            blend_winery_lots_with_chemistry(
                ledger,
                ["cab", "merlot"],
                [_chem("cab", 100.0, 12.0), _chem("syrah", 50.0, 14.0)],
                new_id="bad",
                draws_l=[100.0, 50.0],
                operation_oxygen_delta_mg=0.0,
            )
        self.assertEqual(ledger.movements, [])
        self.assertEqual(ledger.available_volume_l("cab"), 1000.0)
        self.assertEqual(ledger.available_volume_l("merlot"), 1000.0)

    def test_chemistry_failure_is_atomic_for_provenance(self) -> None:
        ledger = self.ledger()
        with self.assertRaises(Exception):
            blend_winery_lots_with_chemistry(
                ledger,
                ["cab", "merlot"],
                [_chem("cab", 100.0, 12.0), _chem("merlot", 50.0, 14.0)],
                new_id="bad",
                draws_l=[100.0, 50.0],
                operation_oxygen_delta_mg=-151.0,
            )
        self.assertEqual(ledger.movements, [])
        self.assertEqual(ledger.available_volume_l("cab"), 1000.0)
        self.assertEqual(ledger.available_volume_l("merlot"), 1000.0)

    def test_provenance_failure_after_chemistry_is_still_atomic(self) -> None:
        ledger = self.ledger()
        with self.assertRaises(WineryProvenanceError):
            blend_winery_lots_with_chemistry(
                ledger,
                ["cab", "merlot"],
                [_chem("cab", 1001.0, 12.0), _chem("merlot", 50.0, 14.0)],
                new_id="bad",
                draws_l=[1001.0, 50.0],
                operation_oxygen_delta_mg=0.0,
            )
        self.assertEqual(ledger.movements, [])
        self.assertEqual(ledger.available_volume_l("cab"), 1000.0)
        self.assertEqual(ledger.available_volume_l("merlot"), 1000.0)

    def test_default_draws_use_current_available_balances_exactly(self) -> None:
        ledger = self.ledger()
        ledger.blend(["cab"], new_id="prior", draws_l=[200.0])
        movement_count = len(ledger.movements)
        result = blend_winery_lots_with_chemistry(
            ledger,
            ["cab", "merlot"],
            [_chem("cab", 800.0, 12.0), _chem("merlot", 1000.0, 14.0)],
            new_id="all-remaining",
            operation_oxygen_delta_mg=0.0,
        )
        self.assertEqual(result.movement.source_draws_l, (800.0, 1000.0))
        self.assertEqual(result.chemistry.volume_l, 1800.0)
        self.assertEqual(len(ledger.movements), movement_count + 1)
        self.assertEqual(ledger.available_volume_l("cab"), 0.0)
        self.assertEqual(ledger.available_volume_l("merlot"), 0.0)


if __name__ == "__main__":
    unittest.main()
