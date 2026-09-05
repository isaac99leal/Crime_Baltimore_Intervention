from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


class PommardLegalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_red_only_standard_and_premier_cru_paths(self):
        standard = self.registry.resolve(
            country="France", appellation="Pommard", variant="standard"
        )
        premier = self.registry.resolve(
            country="France", appellation="Pommard", variant="premier cru"
        )
        self.assertIsNotNone(standard)
        self.assertIsNotNone(premier)
        self.assertEqual(standard.id, "fr:pommard:standard")
        self.assertEqual(premier.id, "fr:pommard:premier-cru")
        self.assertEqual(standard.wine_style, "red")
        self.assertEqual(premier.wine_style, "red")
        self.assertEqual(standard.allowed_grapes, ("Pinot Noir",))
        self.assertEqual(premier.allowed_grapes, ("Pinot Noir",))

    def test_exact_maturity_yield_and_total_alcohol_split(self):
        standard = self.registry.resolve(
            country="France", appellation="Pommard", variant="standard"
        )
        premier = self.registry.resolve(
            country="France", appellation="Pommard", variant="premier cru"
        )
        self.assertIsNotNone(standard)
        self.assertIsNotNone(premier)
        self.assertEqual(
            (standard.min_must_sugar_g_l, standard.min_potential_alcohol_pct, standard.max_yield_hl_ha, standard.max_total_alcohol_pct),
            (180.0, 10.5, 50.0, 13.5),
        )
        self.assertEqual(
            (premier.min_must_sugar_g_l, premier.min_potential_alcohol_pct, premier.max_yield_hl_ha, premier.max_total_alcohol_pct),
            (189.0, 11.0, 48.0, 14.0),
        )

    def test_analytical_and_calendar_rules_are_enforced(self):
        spec = self.registry.resolve(
            country="France", appellation="Pommard", variant="premier cru"
        )
        self.assertIsNotNone(spec)
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
        early = self.registry.validate_release(
            spec,
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
        high_malic = self.registry.validate_release(
            spec,
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
        self.assertFalse(early.eligible)
        self.assertFalse(high_malic.eligible)

    def test_accessory_white_grapes_are_not_cellar_blend_paths(self):
        spec = self.registry.resolve(
            country="France", appellation="Pommard", variant="premier cru"
        )
        self.assertIsNotNone(spec)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible)
        for grape in ("Chardonnay", "Pinot Blanc", "Pinot Gris"):
            self.assertFalse(self.registry.evaluate_blend(spec, {grape: 100}).eligible)


class PommardSiteAndCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = WorldWineKnowledgeCatalog()
        cls.items = AuthoritativeCatalogGenerator(catalog=cls.knowledge).generate(
            as_of_year=2026, include_site_claims=True
        )

    def test_exactly_28_homologated_premier_cru_climats(self):
        official = [
            site for site in self.knowledge.named_sites
            if site.parent == "Pommard"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        ]
        self.assertEqual(len(official), 28)
        self.assertEqual(len({site.name for site in official}), 28)
        self.assertIn("Clos des Epeneaux", {site.name for site in official})
        self.assertIn("Les Rugiens Bas", {site.name for site in official})
        self.assertNotIn("Les Perrières", {site.name for site in official})

    def test_les_perrieres_secondary_listing_is_preserved_but_not_promoted(self):
        discrepancy = [
            site for site in self.knowledge.named_sites
            if site.parent == "Pommard" and site.name == "Les Perrières"
        ]
        self.assertEqual(len(discrepancy), 1)
        self.assertEqual(discrepancy[0].site_type, "secondary_premier_cru_listing")
        self.assertEqual(discrepancy[0].legal_status, "secondary_listing_not_homologated")

    def test_authoritative_catalog_uses_only_the_28_homologated_climats(self):
        rows = [
            item for item in self.items
            if item.legal_spec_id == "fr:pommard:premier-cru"
        ]
        self.assertEqual(len(rows), 29)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in rows), 28)
        vineyards = {item.wine.vineyard for item in rows if item.wine.vineyard}
        self.assertNotIn("Les Perrières", vineyards)
        official_names = {
            site.name for site in self.knowledge.named_sites
            if site.parent == "Pommard"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        }
        self.assertEqual(vineyards, official_names)

    def test_standard_pommard_has_no_premier_cru_site_claim(self):
        rows = [item for item in self.items if item.legal_spec_id == "fr:pommard:standard"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].wine.vineyard, "")


if __name__ == "__main__":
    unittest.main()
