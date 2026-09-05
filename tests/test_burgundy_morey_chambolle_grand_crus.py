from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


RED_AOCS = {
    "Clos de la Roche": ("fr:clos-de-la-roche:grand-cru", 42.0),
    "Clos Saint-Denis": ("fr:clos-saint-denis:grand-cru", 42.0),
    "Bonnes-Mares": ("fr:bonnes-mares:grand-cru", 42.0),
    "Clos des Lambrays": ("fr:clos-des-lambrays:grand-cru", 42.0),
    "Clos de Tart": ("fr:clos-de-tart:grand-cru", 35.0),
}


class MoreyChambolleGrandCruLegalSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_five_red_only_aocs_are_separate_strict_origins(self):
        for appellation, (spec_id, yield_hl_ha) in RED_AOCS.items():
            spec = self.registry.resolve(
                country="France",
                appellation=appellation,
                variant="grand cru",
            )
            self.assertIsNotNone(spec, appellation)
            self.assertEqual(spec.id, spec_id)
            self.assertEqual(spec.wine_style, "red")
            self.assertEqual(spec.allowed_grapes, ("Pinot Noir",))
            self.assertEqual(spec.min_must_sugar_g_l, 198.0)
            self.assertEqual(spec.min_potential_alcohol_pct, 11.5)
            self.assertEqual(spec.max_total_alcohol_pct, 14.5)
            self.assertEqual(spec.max_yield_hl_ha, yield_hl_ha)
            self.assertEqual(spec.max_residual_sugar_g_l, 2.0)
            self.assertEqual(spec.max_malic_acid_g_l, 0.4)
            self.assertEqual(
                (spec.min_elevage_year_offset, spec.min_elevage_until_month, spec.min_elevage_until_day),
                (1, 6, 15),
            )
            self.assertEqual(
                (spec.release_year_offset, spec.earliest_release_month, spec.earliest_release_day),
                (1, 6, 30),
            )

    def test_clos_de_tart_retains_35_hl_ha_and_manual_harvest(self):
        spec = self.registry.resolve(
            country="France", appellation="Clos de Tart", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        self.assertEqual(spec.max_yield_hl_ha, 35.0)
        self.assertTrue(spec.manual_harvest_required)

        self.assertFalse(
            self.registry.validate_production(
                spec,
                wine_yield_hl_ha=35.01,
                must_sugar_g_l=198.0,
                potential_alcohol_pct=11.5,
                require_complete=True,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_release(
                spec,
                total_aging_months=0,
                manual_harvest=False,
                total_alcohol_pct=14.0,
                residual_sugar_g_l=1.0,
                malic_acid_g_l=0.2,
                vintage_year=2025,
                elevage_end_year=2026,
                elevage_end_month=6,
                elevage_end_day=15,
                release_year=2026,
                release_month=6,
                release_day=30,
                require_complete=True,
            ).eligible
        )

    def test_red_paths_reject_accessory_grapes_as_cellar_blends(self):
        for appellation in RED_AOCS:
            spec = self.registry.resolve(
                country="France", appellation=appellation, variant="grand cru"
            )
            self.assertIsNotNone(spec, appellation)
            self.assertTrue(
                self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible
            )
            self.assertFalse(
                self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible
            )

    def test_musigny_has_separate_current_red_and_white_variants(self):
        red = self.registry.resolve(
            country="France", appellation="Musigny", variant="red grand cru"
        )
        white = self.registry.resolve(
            country="France", appellation="Musigny", variant="white grand cru"
        )
        self.assertIsNotNone(red)
        self.assertIsNotNone(white)
        self.assertNotEqual(red.id, white.id)

        self.assertEqual(red.effective_from, "2013-12-02")
        self.assertEqual(red.allowed_grapes, ("Pinot Noir",))
        self.assertEqual(red.min_must_sugar_g_l, 198.0)
        self.assertEqual(red.min_potential_alcohol_pct, 11.5)
        self.assertEqual(red.max_yield_hl_ha, 42.0)
        self.assertEqual(red.max_residual_sugar_g_l, 2.0)
        self.assertEqual(red.max_malic_acid_g_l, 0.4)

        self.assertEqual(white.effective_from, "2013-12-02")
        self.assertEqual(white.allowed_grapes, ("Chardonnay",))
        self.assertEqual(white.min_must_sugar_g_l, 195.0)
        self.assertEqual(white.min_potential_alcohol_pct, 12.0)
        self.assertEqual(white.max_yield_hl_ha, 44.0)
        self.assertEqual(white.max_residual_sugar_g_l, 3.0)
        self.assertIsNone(white.max_malic_acid_g_l)
        self.assertEqual(red.max_total_alcohol_pct, 14.5)
        self.assertEqual(white.max_total_alcohol_pct, 14.5)

    def test_musigny_colors_enforce_different_maturity_and_yield(self):
        red = self.registry.resolve(
            country="France", appellation="Musigny", variant="red grand cru"
        )
        white = self.registry.resolve(
            country="France", appellation="Musigny", variant="white grand cru"
        )
        self.assertIsNotNone(red)
        self.assertIsNotNone(white)

        self.assertFalse(
            self.registry.validate_production(
                red,
                wine_yield_hl_ha=42.1,
                must_sugar_g_l=198.0,
                potential_alcohol_pct=11.5,
                require_complete=True,
            ).eligible
        )
        self.assertTrue(
            self.registry.validate_production(
                white,
                wine_yield_hl_ha=44.0,
                must_sugar_g_l=195.0,
                potential_alcohol_pct=12.0,
                require_complete=True,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                white,
                wine_yield_hl_ha=44.0,
                must_sugar_g_l=194.9,
                potential_alcohol_pct=12.0,
                require_complete=True,
            ).eligible
        )

    def test_exact_calendar_rules_apply_to_cohort(self):
        spec = self.registry.resolve(
            country="France", appellation="Bonnes-Mares", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        early_elevage = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.2,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=14,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        early_release = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.2,
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
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.2,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        self.assertFalse(early_elevage.eligible)
        self.assertFalse(early_release.eligible)
        self.assertTrue(exact.eligible)


class MoreyChambolleGrandCruCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = AuthoritativeCatalogGenerator().generate(
            as_of_year=2026,
            include_site_claims=True,
        )

    def test_one_base_record_per_red_only_aoc(self):
        for appellation, (spec_id, _) in RED_AOCS.items():
            rows = [item for item in self.items if item.legal_spec_id == spec_id]
            self.assertEqual(len(rows), 1, (appellation, len(rows)))
            self.assertEqual(rows[0].wine.appellation, appellation)
            self.assertEqual(rows[0].wine.classification, "grand cru")
            self.assertEqual(rows[0].wine.grapes, ("Pinot Noir",))
            self.assertEqual(rows[0].wine.vineyard, "")

    def test_musigny_generates_one_red_and_one_white_base_record(self):
        red = [
            item for item in self.items
            if item.legal_spec_id == "fr:musigny:red-grand-cru"
        ]
        white = [
            item for item in self.items
            if item.legal_spec_id == "fr:musigny:white-grand-cru"
        ]
        self.assertEqual(len(red), 1)
        self.assertEqual(len(white), 1)
        self.assertEqual(red[0].wine.grapes, ("Pinot Noir",))
        self.assertEqual(white[0].wine.grapes, ("Chardonnay",))
        self.assertEqual(red[0].wine.vineyard, "")
        self.assertEqual(white[0].wine.vineyard, "")

    def test_grand_cru_aocs_do_not_leak_as_communal_site_claims(self):
        prohibited = set(RED_AOCS) | {"Musigny"}
        leaked = [
            (item.wine.appellation, item.wine.vineyard)
            for item in self.items
            if item.wine.appellation in {"Morey-Saint-Denis", "Chambolle-Musigny"}
            and item.wine.vineyard in prohibited
        ]
        self.assertFalse(leaked)


if __name__ == "__main__":
    unittest.main()
