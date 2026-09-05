from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


EXPECTED_SPECS = {
    "white standard": ("fr:savigny-les-beaune:white-standard", 178.0, 11.0, 57.0, 13.5, (4, 15), (4, 30)),
    "red standard": ("fr:savigny-les-beaune:red-standard", 180.0, 10.5, 50.0, 13.5, (5, 15), (5, 31)),
    "white premier cru": ("fr:savigny-les-beaune:white-premier-cru", 187.0, 11.5, 55.0, 14.0, (4, 15), (4, 30)),
    "red premier cru": ("fr:savigny-les-beaune:red-premier-cru", 189.0, 11.0, 48.0, 14.0, (5, 15), (5, 31)),
}


class SavignyLesBeauneLegalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_four_color_level_paths_and_color_specific_calendars(self):
        for variant, (spec_id, sugar, alcohol, yield_hl, total_alcohol, elevage_md, release_md) in EXPECTED_SPECS.items():
            spec = self.registry.resolve(
                country="France", appellation="Savigny-lès-Beaune", variant=variant
            )
            self.assertIsNotNone(spec, variant)
            self.assertEqual(spec.id, spec_id)
            self.assertEqual(spec.min_must_sugar_g_l, sugar)
            self.assertEqual(spec.min_potential_alcohol_pct, alcohol)
            self.assertEqual(spec.max_yield_hl_ha, yield_hl)
            self.assertEqual(spec.max_total_alcohol_pct, total_alcohol)
            self.assertEqual(
                (spec.min_elevage_until_month, spec.min_elevage_until_day), elevage_md
            )
            self.assertEqual(
                (spec.earliest_release_month, spec.earliest_release_day), release_md
            )
            self.assertEqual(spec.min_elevage_year_offset, 1)
            self.assertEqual(spec.release_year_offset, 1)

    def test_white_and_red_composition_paths_are_distinct(self):
        white = self.registry.resolve(
            country="France", appellation="Savigny-lès-Beaune", variant="white premier cru"
        )
        red = self.registry.resolve(
            country="France", appellation="Savigny-lès-Beaune", variant="red premier cru"
        )
        self.assertIsNotNone(white)
        self.assertIsNotNone(red)
        self.assertTrue(self.registry.evaluate_blend(white, {"Chardonnay": 100}).eligible)
        self.assertTrue(self.registry.evaluate_blend(white, {"Pinot Blanc": 100}).eligible)
        self.assertTrue(self.registry.evaluate_blend(red, {"Pinot Noir": 100}).eligible)
        for grape in ("Chardonnay", "Pinot Blanc", "Pinot Gris"):
            self.assertFalse(self.registry.evaluate_blend(red, {grape: 100}).eligible)

    def test_red_malic_and_white_unconditional_sugar_are_enforced(self):
        red = self.registry.resolve(
            country="France", appellation="Savigny-lès-Beaune", variant="red premier cru"
        )
        white = self.registry.resolve(
            country="France", appellation="Savigny-lès-Beaune", variant="white premier cru"
        )
        self.assertIsNotNone(red)
        self.assertIsNotNone(white)
        red_fail = self.registry.validate_release(
            red,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.41,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=5,
            elevage_end_day=15,
            release_year=2026,
            release_month=5,
            release_day=31,
            require_complete=True,
        )
        white_fail = self.registry.validate_release(
            white,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=3.01,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=4,
            elevage_end_day=15,
            release_year=2026,
            release_month=4,
            release_day=30,
            require_complete=True,
        )
        self.assertFalse(red_fail.eligible)
        self.assertFalse(white_fail.eligible)

    def test_white_and_red_exact_release_days_do_not_collapse(self):
        white = self.registry.resolve(
            country="France", appellation="Savigny-les-Beaune", variant="white premier cru"
        )
        red = self.registry.resolve(
            country="France", appellation="Savigny-les-Beaune", variant="red premier cru"
        )
        self.assertIsNotNone(white)
        self.assertIsNotNone(red)
        white_early = self.registry.validate_release(
            white,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=2.0,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=4,
            elevage_end_day=15,
            release_year=2026,
            release_month=4,
            release_day=29,
            require_complete=True,
        )
        red_early = self.registry.validate_release(
            red,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.2,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=5,
            elevage_end_day=15,
            release_year=2026,
            release_month=5,
            release_day=30,
            require_complete=True,
        )
        self.assertFalse(white_early.eligible)
        self.assertFalse(red_early.eligible)


class SavignyLesBeauneSiteAndCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = WorldWineKnowledgeCatalog()
        cls.items = AuthoritativeCatalogGenerator(catalog=cls.knowledge).generate(
            as_of_year=2026, include_site_claims=True
        )

    def test_exactly_22_official_premier_cru_climat_identities(self):
        sites = [
            site for site in self.knowledge.named_sites
            if site.parent == "Savigny-lès-Beaune"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        ]
        self.assertEqual(len(sites), 22)
        self.assertEqual(len({site.name for site in sites}), 22)
        names = {site.name for site in sites}
        self.assertIn("Aux Serpentières", names)
        self.assertIn("Redrescul", names)

    def test_authoritative_catalog_generates_all_climats_for_both_colors(self):
        white = [
            item for item in self.items
            if item.legal_spec_id == "fr:savigny-les-beaune:white-premier-cru"
        ]
        red = [
            item for item in self.items
            if item.legal_spec_id == "fr:savigny-les-beaune:red-premier-cru"
        ]
        self.assertEqual(len(white), 46)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in white), 44)
        self.assertEqual(len(red), 23)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in red), 22)
        official_names = {
            site.name for site in self.knowledge.named_sites
            if site.parent == "Savigny-lès-Beaune"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        }
        self.assertEqual(
            {item.wine.vineyard for item in red if item.wine.vineyard}, official_names
        )

    def test_standard_wines_remain_site_free(self):
        standard_ids = {
            "fr:savigny-les-beaune:white-standard",
            "fr:savigny-les-beaune:red-standard",
        }
        rows = [item for item in self.items if item.legal_spec_id in standard_ids]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(item.wine.vineyard == "" for item in rows))


if __name__ == "__main__":
    unittest.main()
