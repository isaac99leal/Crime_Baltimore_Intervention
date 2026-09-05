from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


EXPECTED_CLIMATS = {
    "Abbaye de Morgeot", "Blanchot dessus", "Bois de Chassagne", "Cailleret",
    "Champs Jendreau", "Chassagne", "Chassagne du Clos Saint-Jean", "Clos Chareau",
    "Clos Pitois", "Clos Saint-Jean", "Dent de Chien", "En Cailleret", "En Remilly",
    "En Virondot", "Ez Crets", "Ez Crottes", "Francemont", "Guerchère",
    "La Boudriotte", "La Cardeuse", "La Chapelle", "La Grande Borne",
    "La Grande Montagne", "La Maltroie", "La Romanée", "La Roquemaure",
    "Les Baudines", "Les Boirettes", "Les Bondues", "Les Brussonnes",
    "Les Champs gain", "Les Chaumées", "Les Chaumes", "Les Chenevottes",
    "Les Combards", "Les Commes", "Les Embazées", "Les Fairendes",
    "Les Grandes Ruchottes", "Les Grands Clos", "Les Macherelles", "Les Murées",
    "Les Pasquelles", "Les Petites Fairendes", "Les Petits Clos", "Les Places",
    "Les Rebichets", "Les Vergers", "Morgeot", "Petingeret", "Tête du Clos",
    "Tonton Marcel", "Vide Bourse", "Vigne Blanche", "Vigne Derrière",
}


class ChassagneLegalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_four_color_level_paths_resolve_with_exact_limits(self):
        expected = {
            "white standard": ("fr:chassagne-montrachet:white-standard", 178.0, 11.0, 57.0, 13.5, 3.0, None),
            "red standard": ("fr:chassagne-montrachet:red-standard", 180.0, 10.5, 50.0, 13.5, 2.0, 0.4),
            "white premier cru": ("fr:chassagne-montrachet:white-premier-cru", 187.0, 11.5, 55.0, 14.0, 3.0, None),
            "red premier cru": ("fr:chassagne-montrachet:red-premier-cru", 189.0, 11.0, 48.0, 14.0, 2.0, 0.4),
        }
        for variant, values in expected.items():
            spec = self.registry.resolve(country="France", appellation="Chassagne-Montrachet", variant=variant)
            self.assertIsNotNone(spec, variant)
            spec_id, must, potential, yield_hl, total_alc, sugar, malic = values
            self.assertEqual(spec.id, spec_id)
            self.assertEqual(spec.min_must_sugar_g_l, must)
            self.assertEqual(spec.min_potential_alcohol_pct, potential)
            self.assertEqual(spec.max_yield_hl_ha, yield_hl)
            self.assertEqual(spec.max_total_alcohol_pct, total_alc)
            self.assertEqual(spec.max_residual_sugar_g_l, sugar)
            self.assertEqual(spec.max_malic_acid_g_l, malic)
            self.assertEqual((spec.min_elevage_year_offset, spec.min_elevage_until_month, spec.min_elevage_until_day), (1, 6, 15))
            self.assertEqual((spec.release_year_offset, spec.earliest_release_month, spec.earliest_release_day), (1, 6, 30))

    def test_white_and_red_composition_paths_are_conservative_and_legal(self):
        white = self.registry.resolve(country="France", appellation="Chassagne-Montrachet", variant="white premier cru")
        red = self.registry.resolve(country="France", appellation="Chassagne-Montrachet", variant="red premier cru")
        self.assertIsNotNone(white)
        self.assertIsNotNone(red)
        self.assertTrue(self.registry.evaluate_blend(white, {"Chardonnay": 100}).eligible)
        self.assertTrue(self.registry.evaluate_blend(white, {"Pinot Blanc": 100}).eligible)
        self.assertTrue(self.registry.evaluate_blend(red, {"Pinot Noir": 100}).eligible)
        self.assertFalse(self.registry.evaluate_blend(red, {"Chardonnay": 100}).eligible)

    def test_premier_cru_maturity_yield_and_calendar_fail_closed(self):
        spec = self.registry.resolve(country="France", appellation="Chassagne-Montrachet", variant="red premier cru")
        self.assertIsNotNone(spec)
        self.assertFalse(self.registry.validate_production(spec, wine_yield_hl_ha=48.1, must_sugar_g_l=189.0, potential_alcohol_pct=11.0, require_complete=True).eligible)
        self.assertFalse(self.registry.validate_production(spec, wine_yield_hl_ha=48.0, must_sugar_g_l=188.9, potential_alcohol_pct=11.0, require_complete=True).eligible)
        self.assertFalse(self.registry.validate_release(
            spec, total_aging_months=0, total_alcohol_pct=14.0,
            residual_sugar_g_l=2.0, malic_acid_g_l=0.4,
            vintage_year=2025, elevage_end_year=2026, elevage_end_month=6, elevage_end_day=14,
            release_year=2026, release_month=6, release_day=30, require_complete=True,
        ).eligible)
        self.assertTrue(self.registry.validate_release(
            spec, total_aging_months=0, total_alcohol_pct=14.0,
            residual_sugar_g_l=2.0, malic_acid_g_l=0.4,
            vintage_year=2025, elevage_end_year=2026, elevage_end_month=6, elevage_end_day=15,
            release_year=2026, release_month=6, release_day=30, require_complete=True,
        ).eligible)


class ChassagneSiteAndCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = WorldWineKnowledgeCatalog()
        cls.items = AuthoritativeCatalogGenerator(catalog=cls.catalog).generate(as_of_year=2026, include_site_claims=True)

    def test_exactly_55_official_premier_cru_climat_identities(self):
        sites = [s for s in self.catalog.named_sites if s.parent == "Chassagne-Montrachet" and s.site_type == "climat"]
        self.assertEqual(len(sites), 55)
        self.assertEqual({s.name for s in sites}, EXPECTED_CLIMATS)
        self.assertTrue(all(s.legal_status == "official_appellation_climat" for s in sites))

    def test_all_55_climats_enter_both_white_and_red_premier_cru_paths(self):
        white_rows = [i for i in self.items if i.legal_spec_id == "fr:chassagne-montrachet:white-premier-cru" and i.wine.vineyard]
        red_rows = [i for i in self.items if i.legal_spec_id == "fr:chassagne-montrachet:red-premier-cru" and i.wine.vineyard]
        self.assertEqual({i.wine.vineyard for i in white_rows}, EXPECTED_CLIMATS)
        self.assertEqual({i.wine.vineyard for i in red_rows}, EXPECTED_CLIMATS)
        self.assertEqual(len(white_rows), 110)  # two legal white single-variety paths x 55 climats
        self.assertEqual(len(red_rows), 55)

    def test_standard_wines_do_not_receive_premier_cru_climat_claims(self):
        standard_ids = {"fr:chassagne-montrachet:white-standard", "fr:chassagne-montrachet:red-standard"}
        leaked = [i for i in self.items if i.legal_spec_id in standard_ids and i.wine.vineyard]
        self.assertFalse(leaked)


if __name__ == "__main__":
    unittest.main()
