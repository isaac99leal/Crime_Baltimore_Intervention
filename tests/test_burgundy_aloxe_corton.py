from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


EXPECTED_SPECS = {
    "white standard": ("fr:aloxe-corton:white-standard", 178.0, 11.0, 57.0, 13.5),
    "red standard": ("fr:aloxe-corton:red-standard", 180.0, 10.5, 50.0, 13.5),
    "white premier cru": ("fr:aloxe-corton:white-premier-cru", 187.0, 11.5, 55.0, 14.0),
    "red premier cru": ("fr:aloxe-corton:red-premier-cru", 189.0, 11.0, 48.0, 14.0),
}


class AloxeCortonLegalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_four_color_level_paths_resolve_with_exact_limits(self):
        for variant, (spec_id, sugar, alcohol, yield_hl, total_alcohol) in EXPECTED_SPECS.items():
            spec = self.registry.resolve(
                country="France", appellation="Aloxe-Corton", variant=variant
            )
            self.assertIsNotNone(spec, variant)
            self.assertEqual(spec.id, spec_id)
            self.assertEqual(spec.min_must_sugar_g_l, sugar)
            self.assertEqual(spec.min_potential_alcohol_pct, alcohol)
            self.assertEqual(spec.max_yield_hl_ha, yield_hl)
            self.assertEqual(spec.max_total_alcohol_pct, total_alcohol)
            self.assertEqual(
                (spec.min_elevage_year_offset, spec.min_elevage_until_month, spec.min_elevage_until_day),
                (1, 6, 15),
            )
            self.assertEqual(
                (spec.release_year_offset, spec.earliest_release_month, spec.earliest_release_day),
                (1, 6, 30),
            )

    def test_white_pinot_blanc_is_accessory_and_capped_at_30_percent(self):
        spec = self.registry.resolve(
            country="France", appellation="Aloxe-Corton", variant="white premier cru"
        )
        self.assertIsNotNone(spec)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible)
        self.assertFalse(self.registry.evaluate_blend(spec, {"Pinot Blanc": 100}).eligible)
        self.assertTrue(
            self.registry.evaluate_blend(spec, {"Chardonnay": 70, "Pinot Blanc": 30}).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(spec, {"Chardonnay": 69, "Pinot Blanc": 31}).eligible
        )

    def test_red_accessory_white_grapes_are_not_cellar_blend_paths(self):
        spec = self.registry.resolve(
            country="France", appellation="Aloxe-Corton", variant="red premier cru"
        )
        self.assertIsNotNone(spec)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible)
        for grape in ("Chardonnay", "Pinot Blanc", "Pinot Gris"):
            self.assertFalse(self.registry.evaluate_blend(spec, {grape: 100}).eligible)

    def test_analytical_and_exact_calendar_rules_are_enforced(self):
        white = self.registry.resolve(
            country="France", appellation="Aloxe-Corton", variant="white premier cru"
        )
        red = self.registry.resolve(
            country="France", appellation="Aloxe-Corton", variant="red premier cru"
        )
        self.assertIsNotNone(white)
        self.assertIsNotNone(red)
        white_sugar_fail = self.registry.validate_release(
            white,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=3.01,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        red_malic_fail = self.registry.validate_release(
            red,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.41,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        early_release = self.registry.validate_release(
            red,
            total_aging_months=0,
            total_alcohol_pct=13.5,
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
        self.assertFalse(white_sugar_fail.eligible)
        self.assertFalse(red_malic_fail.eligible)
        self.assertFalse(early_release.eligible)


class AloxeCortonSiteAndCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = WorldWineKnowledgeCatalog()
        cls.items = AuthoritativeCatalogGenerator(catalog=cls.knowledge).generate(
            as_of_year=2026, include_site_claims=True
        )

    def test_exactly_14_official_premier_cru_climat_identities(self):
        sites = [
            site for site in self.knowledge.named_sites
            if site.parent == "Aloxe-Corton"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        ]
        self.assertEqual(len(sites), 14)
        self.assertEqual(len({site.name for site in sites}), 14)
        names = {site.name for site in sites}
        self.assertIn("Clos des Maréchaudes", names)
        self.assertIn("Les Vercots", names)

    def test_authoritative_catalog_generates_all_14_climats_for_both_colors(self):
        white = [
            item for item in self.items
            if item.legal_spec_id == "fr:aloxe-corton:white-premier-cru"
        ]
        red = [
            item for item in self.items
            if item.legal_spec_id == "fr:aloxe-corton:red-premier-cru"
        ]
        # White Pinot Blanc is accessory, so only the independently legal Chardonnay path is generated.
        self.assertEqual(len(white), 15)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in white), 14)
        self.assertEqual(len(red), 15)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in red), 14)
        official_names = {
            site.name for site in self.knowledge.named_sites
            if site.parent == "Aloxe-Corton"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        }
        self.assertEqual(
            {item.wine.vineyard for item in white if item.wine.vineyard}, official_names
        )
        self.assertEqual(
            {item.wine.vineyard for item in red if item.wine.vineyard}, official_names
        )

    def test_standard_aloxe_is_site_free(self):
        standard_ids = {"fr:aloxe-corton:white-standard", "fr:aloxe-corton:red-standard"}
        rows = [item for item in self.items if item.legal_spec_id in standard_ids]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(item.wine.vineyard == "" for item in rows))

    def test_grand_cru_origins_do_not_leak_back_as_aloxe_site_suffixes(self):
        prohibited = {"Corton", "Corton-Charlemagne", "Charlemagne"}
        leaked = [
            item.wine.vineyard for item in self.items
            if item.wine.appellation == "Aloxe-Corton" and item.wine.vineyard in prohibited
        ]
        self.assertFalse(leaked)


if __name__ == "__main__":
    unittest.main()
