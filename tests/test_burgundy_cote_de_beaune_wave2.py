from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


ALOXE = {
    "Clos des Maréchaudes", "Clos du Chapitre", "La Coutière", "La Maréchaude",
    "La Toppe au Vert", "Les Chaillots", "Les Fournières", "Les Guérets",
    "Les Maréchaudes", "Les Moutottes", "Les Paulands", "Les Petites Folières",
    "Les Valozières", "Les Vercots",
}
PERNAND_WHITE = {
    "Clos Berthet", "Creux de la Net", "En Caradeux", "Ile des Vergelesses",
    "Les Fichots", "Sous Frétille", "Vergelesses", "Village de Pernand",
}
PERNAND_RED = {
    "Creux de la Net", "En Caradeux", "Ile des Vergelesses", "Les Fichots", "Vergelesses",
}
SANTENAY = {
    "Beauregard", "Beaurepaire", "Clos Faubard", "Clos Rousseau",
    "Clos de Tavannes", "Clos des Mouches", "Grand Clos Rousseau", "La Comme",
    "La Maladière", "Les Gravières", "Les Gravières-Clos de Tavannes", "Passetemps",
}


class CoteDeBeauneWave2LegalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_all_twelve_color_level_paths_resolve(self):
        expected = {
            "Aloxe-Corton": {
                "white standard": (178.0, 11.0, 57.0, 13.5, 6, 15, 6, 30),
                "red standard": (180.0, 10.5, 50.0, 13.5, 6, 15, 6, 30),
                "white premier cru": (187.0, 11.5, 55.0, 14.0, 6, 15, 6, 30),
                "red premier cru": (189.0, 11.0, 48.0, 14.0, 6, 15, 6, 30),
            },
            "Pernand-Vergelesses": {
                "white standard": (178.0, 11.0, 57.0, 13.5, 3, 15, 3, 31),
                "red standard": (180.0, 10.5, 50.0, 13.5, 3, 15, 3, 31),
                "white premier cru": (187.0, 11.5, 55.0, 14.0, 6, 15, 6, 30),
                "red premier cru": (189.0, 11.0, 48.0, 14.0, 6, 15, 6, 30),
            },
            "Santenay": {
                "white standard": (178.0, 11.0, 57.0, 13.5, 3, 15, 3, 31),
                "red standard": (180.0, 10.5, 50.0, 13.5, 3, 15, 3, 31),
                "white premier cru": (187.0, 11.5, 55.0, 14.0, 3, 15, 3, 31),
                "red premier cru": (189.0, 11.0, 48.0, 14.0, 3, 15, 3, 31),
            },
        }
        for appellation, variants in expected.items():
            for variant, values in variants.items():
                spec = self.registry.resolve(country="France", appellation=appellation, variant=variant)
                self.assertIsNotNone(spec, (appellation, variant))
                must, potential, yield_hl, total_alc, em, ed, rm, rd = values
                self.assertEqual(spec.min_must_sugar_g_l, must)
                self.assertEqual(spec.min_potential_alcohol_pct, potential)
                self.assertEqual(spec.max_yield_hl_ha, yield_hl)
                self.assertEqual(spec.max_total_alcohol_pct, total_alc)
                self.assertEqual((spec.min_elevage_year_offset, spec.min_elevage_until_month, spec.min_elevage_until_day), (1, em, ed))
                self.assertEqual((spec.release_year_offset, spec.earliest_release_month, spec.earliest_release_day), (1, rm, rd))

    def test_aloxe_white_pinot_blanc_is_capped_at_30_percent(self):
        spec = self.registry.resolve(country="France", appellation="Aloxe-Corton", variant="white premier cru")
        self.assertIsNotNone(spec)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Chardonnay": 70, "Pinot Blanc": 30}).eligible)
        self.assertFalse(self.registry.evaluate_blend(spec, {"Chardonnay": 69, "Pinot Blanc": 31}).eligible)
        self.assertFalse(self.registry.evaluate_blend(spec, {"Pinot Blanc": 100}).eligible)

    def test_red_paths_reject_white_accessory_grapes_as_normal_cellar_blends(self):
        for appellation in ("Aloxe-Corton", "Pernand-Vergelesses", "Santenay"):
            spec = self.registry.resolve(country="France", appellation=appellation, variant="red premier cru")
            self.assertIsNotNone(spec)
            self.assertTrue(self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible)
            self.assertFalse(self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible)

    def test_pernand_and_santenay_do_not_share_premier_cru_release_calendar(self):
        pernand = self.registry.resolve(country="France", appellation="Pernand-Vergelesses", variant="red premier cru")
        santenay = self.registry.resolve(country="France", appellation="Santenay", variant="red premier cru")
        self.assertIsNotNone(pernand)
        self.assertIsNotNone(santenay)
        self.assertEqual((pernand.min_elevage_until_month, pernand.earliest_release_month, pernand.earliest_release_day), (6, 6, 30))
        self.assertEqual((santenay.min_elevage_until_month, santenay.earliest_release_month, santenay.earliest_release_day), (3, 3, 31))


class CoteDeBeauneWave2SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = WorldWineKnowledgeCatalog()
        cls.items = AuthoritativeCatalogGenerator(catalog=cls.catalog).generate(as_of_year=2026, include_site_claims=True)

    def _sites(self, parent: str):
        return [s for s in self.catalog.named_sites if s.parent == parent and s.site_type == "climat"]

    def test_exact_official_identity_counts(self):
        self.assertEqual({s.name for s in self._sites("Aloxe-Corton")}, ALOXE)
        self.assertEqual({s.name for s in self._sites("Pernand-Vergelesses")}, PERNAND_WHITE)
        self.assertEqual({s.name for s in self._sites("Santenay")}, SANTENAY)
        self.assertEqual(len(self._sites("Aloxe-Corton")), 14)
        self.assertEqual(len(self._sites("Pernand-Vergelesses")), 8)
        self.assertEqual(len(self._sites("Santenay")), 12)

    def test_aloxe_all_climats_enter_both_premier_cru_colors(self):
        white = [i for i in self.items if i.legal_spec_id == "fr:aloxe-corton:white-premier-cru" and i.wine.vineyard]
        red = [i for i in self.items if i.legal_spec_id == "fr:aloxe-corton:red-premier-cru" and i.wine.vineyard]
        self.assertEqual({i.wine.vineyard for i in white}, ALOXE)
        self.assertEqual({i.wine.vineyard for i in red}, ALOXE)
        self.assertEqual(len(white), 14)
        self.assertEqual(len(red), 14)

    def test_pernand_enforces_white_only_climats(self):
        white = [i for i in self.items if i.legal_spec_id == "fr:pernand-vergelesses:white-premier-cru" and i.wine.vineyard]
        red = [i for i in self.items if i.legal_spec_id == "fr:pernand-vergelesses:red-premier-cru" and i.wine.vineyard]
        self.assertEqual({i.wine.vineyard for i in white}, PERNAND_WHITE)
        self.assertEqual({i.wine.vineyard for i in red}, PERNAND_RED)
        self.assertEqual(len(white), 16)  # Chardonnay and Pinot Blanc x 8 legal white climats
        self.assertEqual(len(red), 5)
        self.assertFalse({"Clos Berthet", "Sous Frétille", "Village de Pernand"} & {i.wine.vineyard for i in red})

    def test_santenay_all_climats_enter_both_premier_cru_colors(self):
        white = [i for i in self.items if i.legal_spec_id == "fr:santenay:white-premier-cru" and i.wine.vineyard]
        red = [i for i in self.items if i.legal_spec_id == "fr:santenay:red-premier-cru" and i.wine.vineyard]
        self.assertEqual({i.wine.vineyard for i in white}, SANTENAY)
        self.assertEqual({i.wine.vineyard for i in red}, SANTENAY)
        self.assertEqual(len(white), 24)  # Chardonnay and Pinot Blanc x 12 climats
        self.assertEqual(len(red), 12)

    def test_standard_paths_never_receive_premier_cru_climat_claims(self):
        ids = {
            "fr:aloxe-corton:white-standard", "fr:aloxe-corton:red-standard",
            "fr:pernand-vergelesses:white-standard", "fr:pernand-vergelesses:red-standard",
            "fr:santenay:white-standard", "fr:santenay:red-standard",
        }
        leaked = [i for i in self.items if i.legal_spec_id in ids and i.wine.vineyard]
        self.assertFalse(leaked)


if __name__ == "__main__":
    unittest.main()
