from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


EXPECTED_SPECS = {
    "white standard": ("fr:chassagne-montrachet:white-standard", 178.0, 11.0, 57.0, 13.5),
    "red standard": ("fr:chassagne-montrachet:red-standard", 180.0, 10.5, 50.0, 13.5),
    "white premier cru": ("fr:chassagne-montrachet:white-premier-cru", 187.0, 11.5, 55.0, 14.0),
    "red premier cru": ("fr:chassagne-montrachet:red-premier-cru", 189.0, 11.0, 48.0, 14.0),
}


class ChassagneMontrachetLegalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_four_color_level_paths_resolve_with_exact_limits(self):
        for variant, (spec_id, sugar, alcohol, yield_hl, max_total_alcohol) in EXPECTED_SPECS.items():
            spec = self.registry.resolve(
                country="France",
                appellation="Chassagne-Montrachet",
                variant=variant,
            )
            self.assertIsNotNone(spec, variant)
            self.assertEqual(spec.id, spec_id)
            self.assertEqual(spec.min_must_sugar_g_l, sugar)
            self.assertEqual(spec.min_potential_alcohol_pct, alcohol)
            self.assertEqual(spec.max_yield_hl_ha, yield_hl)
            self.assertEqual(spec.max_total_alcohol_pct, max_total_alcohol)
            self.assertEqual(
                (spec.min_elevage_year_offset, spec.min_elevage_until_month, spec.min_elevage_until_day),
                (1, 6, 15),
            )
            self.assertEqual(
                (spec.release_year_offset, spec.earliest_release_month, spec.earliest_release_day),
                (1, 6, 30),
            )

    def test_white_and_red_composition_paths_are_distinct(self):
        white = self.registry.resolve(
            country="France",
            appellation="Chassagne-Montrachet",
            variant="white premier cru",
        )
        red = self.registry.resolve(
            country="France",
            appellation="Chassagne-Montrachet",
            variant="red premier cru",
        )
        self.assertIsNotNone(white)
        self.assertIsNotNone(red)
        self.assertTrue(self.registry.evaluate_blend(white, {"Chardonnay": 100}).eligible)
        self.assertTrue(self.registry.evaluate_blend(white, {"Pinot Blanc": 100}).eligible)
        self.assertTrue(self.registry.evaluate_blend(red, {"Pinot Noir": 100}).eligible)
        self.assertFalse(self.registry.evaluate_blend(red, {"Chardonnay": 100}).eligible)

    def test_red_malic_and_white_unconditional_sugar_limits_are_machine_enforced(self):
        red = self.registry.resolve(
            country="France",
            appellation="Chassagne-Montrachet",
            variant="red premier cru",
        )
        white = self.registry.resolve(
            country="France",
            appellation="Chassagne-Montrachet",
            variant="white premier cru",
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
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        white_fail = self.registry.validate_release(
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
        self.assertFalse(red_fail.eligible)
        self.assertFalse(white_fail.eligible)

    def test_exact_release_calendar_is_enforced(self):
        spec = self.registry.resolve(
            country="France",
            appellation="Chassagne-Montrachet",
            variant="white premier cru",
        )
        self.assertIsNotNone(spec)
        early = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=13.5,
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
            total_alcohol_pct=13.5,
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


class ChassagneMontrachetSiteAndCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = WorldWineKnowledgeCatalog()
        cls.items = AuthoritativeCatalogGenerator(catalog=cls.knowledge).generate(
            as_of_year=2026,
            include_site_claims=True,
        )

    def test_exactly_55_official_premier_cru_climat_identities(self):
        sites = [
            site for site in self.knowledge.named_sites
            if site.parent == "Chassagne-Montrachet"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        ]
        self.assertEqual(len(sites), 55)
        self.assertEqual(len({site.name for site in sites}), 55)
        self.assertIn("Abbaye de Morgeot", {site.name for site in sites})
        self.assertIn("Vigne Derrière", {site.name for site in sites})

    def test_authoritative_catalog_generates_all_55_climats_for_both_colors(self):
        white = [
            item for item in self.items
            if item.legal_spec_id == "fr:chassagne-montrachet:white-premier-cru"
        ]
        red = [
            item for item in self.items
            if item.legal_spec_id == "fr:chassagne-montrachet:red-premier-cru"
        ]
        # White has two individually legal 100% blend paths (Chardonnay and Pinot Blanc):
        # two base records + 55 site records for each blend.
        self.assertEqual(len(white), 112)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in white), 110)
        self.assertEqual(len(red), 56)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in red), 55)
        self.assertEqual({item.wine.vineyard for item in red if item.wine.vineyard}, {
            site.name for site in self.knowledge.named_sites
            if site.parent == "Chassagne-Montrachet"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        })

    def test_standard_wines_do_not_inherit_premier_cru_site_claims(self):
        standard_ids = {
            "fr:chassagne-montrachet:white-standard",
            "fr:chassagne-montrachet:red-standard",
        }
        rows = [item for item in self.items if item.legal_spec_id in standard_ids]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(item.wine.vineyard == "" for item in rows))


if __name__ == "__main__":
    unittest.main()
