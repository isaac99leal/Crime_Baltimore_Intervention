from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


AUXEY = {
    "Bas des Duresses", "Climat du Val", "Clos du Val", "La Chapelle",
    "Les Bréterins", "Les Duresses", "Les Ecussaux", "Les Grands Champs", "Reugne",
}
MONTHELIE = {
    "Clos des Toisières", "La Taupine", "Le Cas Rougeot", "Le Château Gaillard",
    "Le Clos Gauthey", "Le Clou des Chênes", "Le Meix Bataille", "Le Village",
    "Les Barbières", "Les Champs Fulliots", "Les Clous", "Les Duresses",
    "Les Riottes", "Les Vignes Rondes", "Sur la Velle",
}
MARANGES = {
    "Clos de la Boutière", "Clos de la Fussière", "La Fussière",
    "Le Clos des Loyères", "Le Clos des Rois", "Le Croix Moines", "Les Clos Roussots",
}


class CoteDeBeauneWave3LegalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_all_twelve_color_level_paths_resolve_with_exact_limits(self):
        for appellation in ("Auxey-Duresses", "Monthélie"):
            expected = {
                "white standard": (178.0, 11.0, 57.0, 13.5),
                "red standard": (180.0, 10.5, 50.0, 13.5),
                "white premier cru": (187.0, 11.5, 55.0, 14.0),
                "red premier cru": (189.0, 11.0, 48.0, 14.0),
            }
            for variant, (must, potential, yield_hl, total_alc) in expected.items():
                spec = self.registry.resolve(country="France", appellation=appellation, variant=variant)
                self.assertIsNotNone(spec, (appellation, variant))
                self.assertEqual(spec.min_must_sugar_g_l, must)
                self.assertEqual(spec.min_potential_alcohol_pct, potential)
                self.assertEqual(spec.max_yield_hl_ha, yield_hl)
                self.assertEqual(spec.max_total_alcohol_pct, total_alc)
                self.assertEqual((spec.min_elevage_year_offset, spec.min_elevage_until_month, spec.min_elevage_until_day), (1, 6, 15))
                self.assertEqual((spec.release_year_offset, spec.earliest_release_month, spec.earliest_release_day), (1, 6, 30))

        expected_maranges = {
            "white standard": (178.0, 11.0, 57.0, 13.5, 3, 15, 3, 30),
            "red standard": (180.0, 10.5, 50.0, 13.5, 6, 15, 6, 30),
            "white premier cru": (187.0, 11.5, 55.0, 14.0, 3, 15, 3, 30),
            "red premier cru": (189.0, 11.0, 48.0, 14.0, 6, 15, 6, 30),
        }
        for variant, values in expected_maranges.items():
            spec = self.registry.resolve(country="France", appellation="Maranges", variant=variant)
            self.assertIsNotNone(spec, variant)
            must, potential, yield_hl, total_alc, em, ed, rm, rd = values
            self.assertEqual(spec.min_must_sugar_g_l, must)
            self.assertEqual(spec.min_potential_alcohol_pct, potential)
            self.assertEqual(spec.max_yield_hl_ha, yield_hl)
            self.assertEqual(spec.max_total_alcohol_pct, total_alc)
            self.assertEqual((spec.min_elevage_year_offset, spec.min_elevage_until_month, spec.min_elevage_until_day), (1, em, ed))
            self.assertEqual((spec.release_year_offset, spec.earliest_release_month, spec.earliest_release_day), (1, rm, rd))

    def test_white_and_red_composition_paths_stay_conservative(self):
        for appellation in ("Auxey-Duresses", "Monthélie"):
            white = self.registry.resolve(country="France", appellation=appellation, variant="white premier cru")
            red = self.registry.resolve(country="France", appellation=appellation, variant="red premier cru")
            self.assertIsNotNone(white)
            self.assertIsNotNone(red)
            self.assertTrue(self.registry.evaluate_blend(white, {"Chardonnay": 100}).eligible)
            self.assertTrue(self.registry.evaluate_blend(white, {"Pinot Blanc": 100}).eligible)
            self.assertTrue(self.registry.evaluate_blend(red, {"Pinot Noir": 100}).eligible)
            self.assertFalse(self.registry.evaluate_blend(red, {"Chardonnay": 100}).eligible)

        maranges_white = self.registry.resolve(country="France", appellation="Maranges", variant="white premier cru")
        maranges_red = self.registry.resolve(country="France", appellation="Maranges", variant="red premier cru")
        self.assertIsNotNone(maranges_white)
        self.assertIsNotNone(maranges_red)
        self.assertTrue(self.registry.evaluate_blend(maranges_white, {"Chardonnay": 100}).eligible)
        self.assertFalse(self.registry.evaluate_blend(maranges_white, {"Pinot Blanc": 100}).eligible)
        self.assertTrue(self.registry.evaluate_blend(maranges_red, {"Pinot Noir": 100}).eligible)

    def test_maranges_white_and_red_release_calendars_are_color_specific(self):
        white = self.registry.resolve(country="France", appellation="Maranges", variant="white premier cru")
        red = self.registry.resolve(country="France", appellation="Maranges", variant="red premier cru")
        self.assertIsNotNone(white)
        self.assertIsNotNone(red)

        early_white = self.registry.validate_release(
            white,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=2.0,
            vintage_year=2025,
            elevage_end_year=2026, elevage_end_month=3, elevage_end_day=15,
            release_year=2026, release_month=3, release_day=29,
            require_complete=True,
        )
        exact_white = self.registry.validate_release(
            white,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=2.0,
            vintage_year=2025,
            elevage_end_year=2026, elevage_end_month=3, elevage_end_day=15,
            release_year=2026, release_month=3, release_day=30,
            require_complete=True,
        )
        early_red = self.registry.validate_release(
            red,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.2,
            vintage_year=2025,
            elevage_end_year=2026, elevage_end_month=6, elevage_end_day=15,
            release_year=2026, release_month=6, release_day=29,
            require_complete=True,
        )
        exact_red = self.registry.validate_release(
            red,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.2,
            vintage_year=2025,
            elevage_end_year=2026, elevage_end_month=6, elevage_end_day=15,
            release_year=2026, release_month=6, release_day=30,
            require_complete=True,
        )
        self.assertFalse(early_white.eligible)
        self.assertTrue(exact_white.eligible)
        self.assertFalse(early_red.eligible)
        self.assertTrue(exact_red.eligible)


class CoteDeBeauneWave3SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = WorldWineKnowledgeCatalog()
        cls.items = AuthoritativeCatalogGenerator(catalog=cls.catalog).generate(as_of_year=2026, include_site_claims=True)

    def _sites(self, parent: str):
        return [s for s in self.catalog.named_sites if s.parent == parent and s.site_type == "climat"]

    def test_exact_official_identity_counts(self):
        self.assertEqual({s.name for s in self._sites("Auxey-Duresses")}, AUXEY)
        self.assertEqual({s.name for s in self._sites("Monthélie")}, MONTHELIE)
        self.assertEqual({s.name for s in self._sites("Maranges")}, MARANGES)
        self.assertEqual(len(self._sites("Auxey-Duresses")), 9)
        self.assertEqual(len(self._sites("Monthélie")), 15)
        self.assertEqual(len(self._sites("Maranges")), 7)

    def test_auxey_all_climats_enter_both_colors(self):
        white = [i for i in self.items if i.legal_spec_id == "fr:auxey-duresses:white-premier-cru" and i.wine.vineyard]
        red = [i for i in self.items if i.legal_spec_id == "fr:auxey-duresses:red-premier-cru" and i.wine.vineyard]
        self.assertEqual({i.wine.vineyard for i in white}, AUXEY)
        self.assertEqual({i.wine.vineyard for i in red}, AUXEY)
        self.assertEqual(len(white), 18)
        self.assertEqual(len(red), 9)

    def test_monthelie_all_climats_enter_both_colors(self):
        white = [i for i in self.items if i.legal_spec_id == "fr:monthelie:white-premier-cru" and i.wine.vineyard]
        red = [i for i in self.items if i.legal_spec_id == "fr:monthelie:red-premier-cru" and i.wine.vineyard]
        self.assertEqual({i.wine.vineyard for i in white}, MONTHELIE)
        self.assertEqual({i.wine.vineyard for i in red}, MONTHELIE)
        self.assertEqual(len(white), 30)
        self.assertEqual(len(red), 15)

    def test_maranges_all_climats_enter_both_colors(self):
        white = [i for i in self.items if i.legal_spec_id == "fr:maranges:white-premier-cru" and i.wine.vineyard]
        red = [i for i in self.items if i.legal_spec_id == "fr:maranges:red-premier-cru" and i.wine.vineyard]
        self.assertEqual({i.wine.vineyard for i in white}, MARANGES)
        self.assertEqual({i.wine.vineyard for i in red}, MARANGES)
        self.assertEqual(len(white), 7)
        self.assertEqual(len(red), 7)

    def test_standard_paths_do_not_receive_premier_cru_claims(self):
        ids = {
            "fr:auxey-duresses:white-standard", "fr:auxey-duresses:red-standard",
            "fr:monthelie:white-standard", "fr:monthelie:red-standard",
            "fr:maranges:white-standard", "fr:maranges:red-standard",
        }
        self.assertFalse([i for i in self.items if i.legal_spec_id in ids and i.wine.vineyard])


if __name__ == "__main__":
    unittest.main()
