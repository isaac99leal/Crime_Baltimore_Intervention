from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


EXPECTED_SPECS = {
    "white standard": ("fr:beaune:white-standard", 178.0, 11.0, 57.0, 13.5),
    "red standard": ("fr:beaune:red-standard", 180.0, 10.5, 50.0, 13.5),
    "white premier cru": ("fr:beaune:white-premier-cru", 187.0, 11.5, 55.0, 14.0),
    "red premier cru": ("fr:beaune:red-premier-cru", 189.0, 11.0, 48.0, 14.0),
}


class BeauneLegalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_four_color_level_paths_resolve_with_exact_limits(self):
        for variant, (spec_id, sugar, alcohol, yield_hl, max_total_alcohol) in EXPECTED_SPECS.items():
            spec = self.registry.resolve(
                country="France", appellation="Beaune", variant=variant
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

    def test_white_pinot_gris_is_accessory_not_standalone(self):
        spec = self.registry.resolve(
            country="France", appellation="Beaune", variant="white premier cru"
        )
        self.assertIsNotNone(spec)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Pinot Blanc": 100}).eligible)
        self.assertFalse(self.registry.evaluate_blend(spec, {"Pinot Gris": 100}).eligible)
        self.assertTrue(
            self.registry.evaluate_blend(
                spec, {"Chardonnay": 70, "Pinot Gris": 30}
            ).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(
                spec, {"Chardonnay": 60, "Pinot Gris": 40}
            ).eligible
        )

    def test_red_path_rejects_accessory_white_grapes_as_cellar_blends(self):
        spec = self.registry.resolve(
            country="France", appellation="Beaune", variant="red premier cru"
        )
        self.assertIsNotNone(spec)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible)
        for grape in ("Chardonnay", "Pinot Blanc", "Pinot Gris"):
            self.assertFalse(self.registry.evaluate_blend(spec, {grape: 100}).eligible)

    def test_red_malic_white_sugar_and_exact_release_date_are_enforced(self):
        red = self.registry.resolve(
            country="France", appellation="Beaune", variant="red premier cru"
        )
        white = self.registry.resolve(
            country="France", appellation="Beaune", variant="white premier cru"
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
        early_release = self.registry.validate_release(
            white,
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
        self.assertFalse(red_fail.eligible)
        self.assertFalse(white_sugar_fail.eligible)
        self.assertFalse(early_release.eligible)


class BeauneSiteAndCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = WorldWineKnowledgeCatalog()
        cls.items = AuthoritativeCatalogGenerator(catalog=cls.knowledge).generate(
            as_of_year=2026, include_site_claims=True
        )

    def test_exactly_42_official_premier_cru_climat_identities(self):
        sites = [
            site for site in self.knowledge.named_sites
            if site.parent == "Beaune"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        ]
        self.assertEqual(len(sites), 42)
        self.assertEqual(len({site.name for site in sites}), 42)
        names = {site.name for site in sites}
        self.assertIn("Clos du Roi", names)
        self.assertIn("Le Clos des Mouches", names)
        self.assertIn("Sur les Grèves-Clos Sainte-Anne", names)

    def test_authoritative_catalog_generates_all_climats_for_both_colors(self):
        white = [
            item for item in self.items
            if item.legal_spec_id == "fr:beaune:white-premier-cru"
        ]
        red = [
            item for item in self.items
            if item.legal_spec_id == "fr:beaune:red-premier-cru"
        ]
        # Chardonnay and Pinot Blanc are independently valid 100% white paths;
        # Pinot Gris is accessory and therefore does not generate a standalone path.
        self.assertEqual(len(white), 86)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in white), 84)
        self.assertEqual(len(red), 43)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in red), 42)
        site_names = {
            site.name for site in self.knowledge.named_sites
            if site.parent == "Beaune"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        }
        self.assertEqual(
            {item.wine.vineyard for item in red if item.wine.vineyard}, site_names
        )

    def test_standard_beaune_is_site_free(self):
        standard_ids = {"fr:beaune:white-standard", "fr:beaune:red-standard"}
        rows = [item for item in self.items if item.legal_spec_id in standard_ids]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(item.wine.vineyard == "" for item in rows))


if __name__ == "__main__":
    unittest.main()
