from __future__ import annotations

import unittest
from dataclasses import replace

from sommelier_v2.domain import WineRecord, WineStyle
from sommelier_v2.knowledge.finished_wine import (
    FinishedWineAssembler,
    FinishedWineConstraintError,
    ValidatedWineRecord,
)
from sommelier_v2.knowledge.jurisdiction_labels import BlendComponent, LabelClaims


def c(pct, grape, country, origins=(), vintage=None):
    return BlendComponent(float(pct), grape, country, tuple(origins), vintage)


def prototype(country: str, *, region: str = "", appellation: str = "", vintage: int = 0) -> WineRecord:
    return WineRecord(
        id="wine:test",
        producer="Test Estate",
        label="Estate Selection",
        country=country,
        region=region,
        appellation=appellation,
        vintage=vintage,
        style=WineStyle.RED,
    )


class FinishedWineAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assembler = FinishedWineAssembler()

    def test_napa_ava_wine_is_constructed_from_physical_ledger(self):
        components = [
            c(95, "Cabernet Sauvignon", "United States", ("Napa Valley", "California"), 2025),
            c(5, "Merlot", "United States", ("California",), 2024),
        ]
        claims = LabelClaims(
            jurisdiction="US",
            origin_names=("Napa Valley",),
            origin_type="AVA",
            variety_names=("Cabernet Sauvignon",),
            vintage_years=(2025,),
            fully_finished_in_required_area=True,
        )
        wine = self.assembler.assemble(prototype("United States"), components=components, claims=claims)
        self.assertIsInstance(wine, WineRecord)
        self.assertIsInstance(wine, ValidatedWineRecord)
        self.assertEqual(wine.appellation, "Napa Valley")
        self.assertEqual(wine.vintage, 2025)
        self.assertEqual(wine.grapes, ("Cabernet Sauvignon", "Merlot"))
        self.assertEqual(len(wine.provenance_components), 2)
        self.assertEqual(len(wine.provenance_fingerprint), 64)
        self.assertTrue(self.assembler.validate_existing(wine).eligible)

    def test_ava_vintage_failure_blocks_record_construction(self):
        components = [
            c(94, "Cabernet Sauvignon", "United States", ("Napa Valley", "California"), 2025),
            c(6, "Cabernet Sauvignon", "United States", ("Napa Valley", "California"), 2024),
        ]
        claims = LabelClaims(
            jurisdiction="US",
            origin_names=("Napa Valley",),
            origin_type="AVA",
            vintage_years=(2025,),
            fully_finished_in_required_area=True,
        )
        with self.assertRaises(FinishedWineConstraintError):
            self.assembler.assemble(prototype("United States"), components=components, claims=claims)

    def test_fabricated_ava_is_rejected_even_when_percentages_work(self):
        components = [
            c(100, "Cabernet Sauvignon", "United States", ("Imaginary Hills", "California"), 2025),
        ]
        claims = LabelClaims(
            jurisdiction="US",
            origin_names=("Imaginary Hills",),
            origin_type="AVA",
            variety_names=("Cabernet Sauvignon",),
            vintage_years=(2025,),
            fully_finished_in_required_area=True,
        )
        with self.assertRaisesRegex(FinishedWineConstraintError, "TTB established-AVA"):
            self.assembler.assemble(prototype("United States"), components=components, claims=claims)

    def test_australian_alias_claim_uses_identity_graph_but_preserves_label_spelling(self):
        components = [
            c(90, "Syrah", "Australia", ("Barossa Valley", "South Australia"), 2025),
            c(10, "Grenache", "Australia", ("McLaren Vale", "South Australia"), 2025),
        ]
        claims = LabelClaims(
            jurisdiction="Australia",
            origin_names=("Barossa Valley",),
            variety_names=("Shiraz",),
            vintage_years=(2025,),
        )
        wine = self.assembler.assemble(prototype("Australia"), components=components, claims=claims)
        self.assertEqual(wine.appellation, "Barossa Valley")
        self.assertIn("Shiraz", wine.front_label_lines)
        self.assertTrue(self.assembler.validate_existing(wine).eligible)

    def test_fabricated_australian_gi_is_rejected(self):
        components = [c(100, "Shiraz", "Australia", ("Imaginary Ranges",), 2025)]
        claims = LabelClaims(
            jurisdiction="Australia",
            origin_names=("Imaginary Ranges",),
            variety_names=("Shiraz",),
            vintage_years=(2025,),
        )
        with self.assertRaisesRegex(FinishedWineConstraintError, "Wine Australia protected-GI"):
            self.assembler.assemble(prototype("Australia"), components=components, claims=claims)

    def test_registered_nz_gi_is_checked_against_iponz_before_assembly(self):
        components = [
            c(85, "Pinot Noir", "New Zealand", ("Marlborough",), 2025),
            c(15, "Chardonnay", "New Zealand", ("Nelson",), 2024),
        ]
        claims = LabelClaims(
            jurisdiction="New Zealand",
            origin_names=("Marlborough",),
            variety_names=("Pinot Noir",),
            vintage_years=(2025,),
            registered_nz_gi=True,
        )
        wine = self.assembler.assemble(prototype("New Zealand"), components=components, claims=claims)
        self.assertEqual(wine.appellation, "Marlborough")
        self.assertTrue(self.assembler.validate_existing(wine).eligible)

        fake_claims = replace(claims, origin_names=("Imaginary Marlborough Foothills",))
        fake_components = [
            c(100, "Pinot Noir", "New Zealand", ("Imaginary Marlborough Foothills",), 2025),
        ]
        with self.assertRaisesRegex(FinishedWineConstraintError, "IPONZ registered wine-GI"):
            self.assembler.assemble(prototype("New Zealand"), components=fake_components, claims=fake_claims)

    def test_provenance_fingerprint_detects_post_validation_tampering(self):
        components = [
            c(100, "Cabernet Sauvignon", "United States", ("Napa Valley", "California"), 2025),
        ]
        claims = LabelClaims(
            jurisdiction="US",
            origin_names=("Napa Valley",),
            origin_type="AVA",
            variety_names=("Cabernet Sauvignon",),
            vintage_years=(2025,),
            fully_finished_in_required_area=True,
        )
        wine = self.assembler.assemble(prototype("United States"), components=components, claims=claims)
        tampered = replace(
            wine,
            provenance_components=(
                c(90, "Cabernet Sauvignon", "United States", ("Napa Valley", "California"), 2025),
                c(10, "Merlot", "United States", ("California",), 2024),
            ),
        )
        decision = self.assembler.validate_existing(tampered)
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.status, "provenance_fingerprint_mismatch")

    def test_display_percentages_are_derived_from_same_component_ledger(self):
        components = [
            c(60, "Cabernet Sauvignon", "United States", ("California",), 2025),
            c(40, "Merlot", "United States", ("California",), 2025),
        ]
        claims = LabelClaims(
            jurisdiction="US",
            origin_names=("California",),
            origin_type="state",
            variety_names=("Cabernet Sauvignon", "Merlot"),
            shown_variety_percentages=True,
            fully_finished_in_required_area=True,
        )
        wine = self.assembler.assemble(prototype("United States"), components=components, claims=claims)
        self.assertTrue(any("60% Cabernet Sauvignon" in line for line in wine.front_label_lines))
        self.assertTrue(any("40% Merlot" in line for line in wine.front_label_lines))


if __name__ == "__main__":
    unittest.main()
