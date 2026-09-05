from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


LOWER_MATURITY = {
    "Bâtard-Montrachet": "fr:batard-montrachet:grand-cru",
    "Bienvenues-Bâtard-Montrachet": "fr:bienvenues-batard-montrachet:grand-cru",
    "Criots-Bâtard-Montrachet": "fr:criots-batard-montrachet:grand-cru",
}

HIGHER_MATURITY = {
    "Chevalier-Montrachet": "fr:chevalier-montrachet:grand-cru",
}


class MontrachetFamilyGrandCruLegalSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_batard_family_lower_maturity_tier_is_exact(self):
        for appellation, spec_id in LOWER_MATURITY.items():
            spec = self.registry.resolve(
                country="France", appellation=appellation, variant="grand cru"
            )
            self.assertIsNotNone(spec, appellation)
            self.assertEqual(spec.id, spec_id)
            self.assertEqual(spec.wine_style, "white")
            self.assertEqual(spec.allowed_grapes, ("Chardonnay",))
            self.assertEqual(spec.min_must_sugar_g_l, 187.0)
            self.assertEqual(spec.min_potential_alcohol_pct, 11.5)
            self.assertEqual(spec.max_yield_hl_ha, 48.0)
            self.assertEqual(spec.max_total_alcohol_pct, 14.5)
            self.assertEqual(spec.max_residual_sugar_g_l, 3.0)
            self.assertEqual(
                (
                    spec.min_elevage_year_offset,
                    spec.min_elevage_until_month,
                    spec.min_elevage_until_day,
                ),
                (1, 6, 15),
            )
            self.assertEqual(
                (
                    spec.release_year_offset,
                    spec.earliest_release_month,
                    spec.earliest_release_day,
                ),
                (1, 6, 30),
            )

    def test_chevalier_uses_higher_maturity_tier(self):
        spec = self.registry.resolve(
            country="France", appellation="Chevalier-Montrachet", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        self.assertEqual(spec.id, "fr:chevalier-montrachet:grand-cru")
        self.assertEqual(spec.allowed_grapes, ("Chardonnay",))
        self.assertEqual(spec.min_must_sugar_g_l, 195.0)
        self.assertEqual(spec.min_potential_alcohol_pct, 12.0)
        self.assertEqual(spec.max_yield_hl_ha, 48.0)
        self.assertEqual(spec.max_total_alcohol_pct, 14.5)
        self.assertEqual(spec.max_residual_sugar_g_l, 3.0)

    def test_charlemagne_is_separate_and_caps_pinot_blanc(self):
        spec = self.registry.resolve(
            country="France", appellation="Charlemagne", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        self.assertEqual(spec.id, "fr:charlemagne:grand-cru")
        self.assertEqual(spec.wine_style, "white")
        self.assertEqual(spec.allowed_grapes, ("Chardonnay", "Pinot Blanc"))
        self.assertEqual(spec.min_must_sugar_g_l, 195.0)
        self.assertEqual(spec.min_potential_alcohol_pct, 12.0)
        self.assertEqual(spec.max_yield_hl_ha, 48.0)
        self.assertTrue(
            self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible
        )
        self.assertTrue(
            self.registry.evaluate_blend(
                spec, {"Chardonnay": 70, "Pinot Blanc": 30}
            ).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(
                spec, {"Chardonnay": 69, "Pinot Blanc": 31}
            ).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(spec, {"Pinot Blanc": 100}).eligible
        )

    def test_exact_calendar_gate_applies_to_white_grand_crus(self):
        spec = self.registry.resolve(
            country="France", appellation="Bâtard-Montrachet", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        early = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=2.0,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=29,
            require_complete=True,
        )
        exact = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=2.0,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        self.assertFalse(early.eligible)
        self.assertTrue(exact.eligible)

    def test_all_chardonnay_only_paths_reject_other_cellar_blends(self):
        for appellation in (*LOWER_MATURITY, *HIGHER_MATURITY):
            spec = self.registry.resolve(
                country="France", appellation=appellation, variant="grand cru"
            )
            self.assertIsNotNone(spec, appellation)
            self.assertTrue(
                self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible
            )
            self.assertFalse(
                self.registry.evaluate_blend(spec, {"Pinot Blanc": 100}).eligible
            )


class MontrachetFamilyGrandCruCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = AuthoritativeCatalogGenerator().generate(
            as_of_year=2026, include_site_claims=True
        )

    def test_each_new_aoc_has_one_authoritative_base_record(self):
        expected = {
            **LOWER_MATURITY,
            **HIGHER_MATURITY,
            "Charlemagne": "fr:charlemagne:grand-cru",
        }
        for appellation, spec_id in expected.items():
            rows = [item for item in self.items if item.legal_spec_id == spec_id]
            self.assertEqual(len(rows), 1, (appellation, len(rows)))
            self.assertEqual(rows[0].wine.appellation, appellation)
            self.assertEqual(rows[0].wine.classification, "grand cru")
            self.assertEqual(rows[0].wine.vineyard, "")

    def test_chardonnay_only_aocs_emit_chardonnay(self):
        for appellation, spec_id in {**LOWER_MATURITY, **HIGHER_MATURITY}.items():
            rows = [item for item in self.items if item.legal_spec_id == spec_id]
            self.assertEqual(len(rows), 1, appellation)
            self.assertEqual(rows[0].wine.grapes, ("Chardonnay",))

    def test_charlemagne_default_positive_path_is_chardonnay(self):
        rows = [
            item for item in self.items if item.legal_spec_id == "fr:charlemagne:grand-cru"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].wine.grapes, ("Chardonnay",))


if __name__ == "__main__":
    unittest.main()
