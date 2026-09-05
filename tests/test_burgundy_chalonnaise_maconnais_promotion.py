from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory


class ChalonnaiseMaconnaisStrictSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_pouilly_fuisse_standard_and_premier_cru(self):
        standard = self.registry.resolve(country="France", appellation="Pouilly-Fuissé", variant="standard")
        premier = self.registry.resolve(country="France", appellation="Pouilly-Fuissé", variant="premier cru")
        self.assertIsNotNone(standard)
        self.assertIsNotNone(premier)
        self.assertEqual((standard.min_potential_alcohol_pct, standard.max_yield_hl_ha, standard.max_residual_sugar_g_l), (11.0, 60.0, 3.0))
        self.assertEqual((premier.min_potential_alcohol_pct, premier.max_yield_hl_ha, premier.max_residual_sugar_g_l), (12.0, 56.0, 3.0))
        self.assertTrue(self.registry.evaluate_blend(standard, "Chardonnay").eligible)
        self.assertFalse(self.registry.evaluate_blend(standard, "Pinot Noir").eligible)

    def test_mercurey_color_and_level_limits(self):
        expected = {
            "white standard": (11.0, 57.0, 3.0, None),
            "red standard": (10.5, 50.0, 2.0, 0.4),
            "white premier cru": (11.5, 55.0, 3.0, None),
            "red premier cru": (11.0, 48.0, 2.0, 0.4),
        }
        for variant, values in expected.items():
            spec = self.registry.resolve(country="France", appellation="Mercurey", variant=variant)
            self.assertIsNotNone(spec, variant)
            self.assertEqual((spec.min_potential_alcohol_pct, spec.max_yield_hl_ha, spec.max_residual_sugar_g_l, spec.max_malic_acid_g_l), values)

    def test_givry_color_and_level_limits(self):
        expected = {
            "white standard": (11.0, 60.0, 3.0, None),
            "red standard": (10.5, 54.0, 2.0, 0.4),
            "white premier cru": (11.5, 58.0, 3.0, None),
            "red premier cru": (11.0, 52.0, 2.0, 0.4),
        }
        for variant, values in expected.items():
            spec = self.registry.resolve(country="France", appellation="Givry", variant=variant)
            self.assertIsNotNone(spec, variant)
            self.assertEqual((spec.min_potential_alcohol_pct, spec.max_yield_hl_ha, spec.max_residual_sugar_g_l, spec.max_malic_acid_g_l), values)

    def test_montagny_is_white_chardonnay_only(self):
        standard = self.registry.resolve(country="France", appellation="Montagny", variant="standard")
        premier = self.registry.resolve(country="France", appellation="Montagny", variant="premier cru")
        self.assertIsNotNone(standard)
        self.assertIsNotNone(premier)
        self.assertEqual((standard.min_potential_alcohol_pct, standard.max_yield_hl_ha), (11.0, 60.0))
        self.assertEqual((premier.min_potential_alcohol_pct, premier.max_yield_hl_ha), (11.5, 58.0))
        self.assertTrue(self.registry.evaluate_blend(standard, "Chardonnay").eligible)
        self.assertFalse(self.registry.evaluate_blend(standard, "Pinot Noir").eligible)


class ChalonnaiseMaconnaisSiteClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()

    @classmethod
    def site(cls, parent: str, name: str, site_type: str = "climat"):
        return next(
            site for site in cls.factory.catalog.named_sites
            if site.parent == parent and site.name == name and site.site_type == site_type
        )

    def test_pouilly_fuisse_premier_cru_climat_passes(self):
        site = self.site("Pouilly-Fuissé", "Les Perrières")
        origin = self.factory.create(OriginRequest(
            country="France", region=site.region, appellation="Pouilly-Fuissé",
            grapes={"Chardonnay": 100}, vintage_year=2025,
            label_scope="regulated_gi", site_id=site.id, wine_variant="premier cru",
        ))
        self.assertTrue(origin.site_claim_eligible)

    def test_mercurey_premier_cru_climat_passes_for_both_colors(self):
        site = self.site("Mercurey", "Le Clos du Roy")
        for variant, grapes in (("white premier cru", {"Chardonnay": 100}), ("red premier cru", {"Pinot Noir": 100})):
            origin = self.factory.create(OriginRequest(
                country="France", region=site.region, appellation="Mercurey",
                grapes=grapes, vintage_year=2025, label_scope="regulated_gi",
                site_id=site.id, wine_variant=variant,
            ))
            self.assertTrue(origin.site_claim_eligible, variant)

    def test_givry_premier_cru_climat_passes_for_both_colors(self):
        site = self.site("Givry", "Clos Salomon")
        for variant, grapes in (("white premier cru", {"Chardonnay": 100}), ("red premier cru", {"Pinot Noir": 100})):
            origin = self.factory.create(OriginRequest(
                country="France", region=site.region, appellation="Givry",
                grapes=grapes, vintage_year=2025, label_scope="regulated_gi",
                site_id=site.id, wine_variant=variant,
            ))
            self.assertTrue(origin.site_claim_eligible, variant)

    def test_montagny_premier_cru_climat_passes(self):
        site = self.site("Montagny", "Les Coères")
        origin = self.factory.create(OriginRequest(
            country="France", region=site.region, appellation="Montagny",
            grapes={"Chardonnay": 100}, vintage_year=2025,
            label_scope="regulated_gi", site_id=site.id, wine_variant="premier cru",
        ))
        self.assertTrue(origin.site_claim_eligible)

    def test_generic_lieux_dits_remain_fail_closed(self):
        cases = (
            ("Pouilly-Fuissé", "Au Bourg", "standard", {"Chardonnay": 100}),
            ("Mercurey", "Chamirey", "red standard", {"Pinot Noir": 100}),
            ("Givry", "La Corvée", "red standard", {"Pinot Noir": 100}),
        )
        for parent, name, variant, grapes in cases:
            site = self.site(parent, name, "lieu_dit")
            origin = self.factory.create(OriginRequest(
                country="France", region=site.region, appellation=parent,
                grapes=grapes, vintage_year=2025, label_scope="regulated_gi",
                site_id=site.id, wine_variant=variant,
            ))
            self.assertFalse(origin.site_claim_eligible, (parent, name))
            self.assertEqual(origin.site_claim_status, "site_claim_rule_unverified")


class ChalonnaiseMaconnaisCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = AuthoritativeCatalogGenerator()
        cls.items = cls.generator.generate(as_of_year=2026, include_site_claims=True)

    def sites(self, spec_id: str) -> set[str]:
        return {item.wine.vineyard for item in self.items if item.legal_spec_id == spec_id and item.wine.vineyard}

    def test_exact_current_seed_counts(self):
        self.assertEqual(len(self.sites("fr:pouilly-fuisse:premier-cru")), 22)
        self.assertEqual(len(self.sites("fr:mercurey:white-premier-cru")), 32)
        self.assertEqual(len(self.sites("fr:mercurey:red-premier-cru")), 32)
        self.assertEqual(len(self.sites("fr:givry:white-premier-cru")), 38)
        self.assertEqual(len(self.sites("fr:givry:red-premier-cru")), 38)
        self.assertEqual(len(self.sites("fr:montagny:premier-cru")), 49)

    def test_mercurey_current_legal_list_gap_is_not_silently_fabricated(self):
        all_mercurey = {
            site.name for site in self.generator.catalog.named_sites
            if site.parent == "Mercurey" and site.site_type == "climat"
        }
        self.assertEqual(len(all_mercurey), 32)
        self.assertNotIn("Clos du Château de Montaigu", all_mercurey)
        spec = self.generator.legal_specs.resolve(country="France", appellation="Mercurey", variant="white premier cru")
        self.assertIsNotNone(spec)
        self.assertIn("33 climats", spec.notes)


if __name__ == "__main__":
    unittest.main()
