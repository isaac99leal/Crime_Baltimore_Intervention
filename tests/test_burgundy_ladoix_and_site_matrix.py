from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory


class LadoixStrictSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_ladoix_color_and_level_limits(self):
        expected = {
            "white standard": (11.0, 57.0, 3.0, None),
            "red standard": (10.5, 50.0, 2.0, 0.4),
            "white premier cru": (11.5, 55.0, 3.0, None),
            "red premier cru": (11.0, 48.0, 2.0, 0.4),
        }
        for variant, values in expected.items():
            spec = self.registry.resolve(
                country="France", appellation="Ladoix", variant=variant
            )
            self.assertIsNotNone(spec, variant)
            self.assertEqual(
                (
                    spec.min_potential_alcohol_pct,
                    spec.max_yield_hl_ha,
                    spec.max_residual_sugar_g_l,
                    spec.max_malic_acid_g_l,
                ),
                values,
            )
            self.assertEqual(spec.release_year_offset, 1)

    def test_ladoix_positive_blends_remain_conservative(self):
        white = self.registry.resolve(
            country="France", appellation="Ladoix", variant="white premier cru"
        )
        red = self.registry.resolve(
            country="France", appellation="Ladoix", variant="red premier cru"
        )
        self.assertIsNotNone(white)
        self.assertIsNotNone(red)
        self.assertTrue(self.registry.evaluate_blend(white, "Chardonnay").eligible)
        self.assertTrue(self.registry.evaluate_blend(white, "Pinot Blanc").eligible)
        self.assertFalse(self.registry.evaluate_blend(white, "Pinot Gris").eligible)
        self.assertTrue(self.registry.evaluate_blend(red, "Pinot Noir").eligible)
        self.assertFalse(self.registry.evaluate_blend(red, "Chardonnay").eligible)


class LadoixSiteMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()

    @classmethod
    def site(cls, name: str, site_type: str = "climat"):
        return next(
            site
            for site in cls.factory.catalog.named_sites
            if site.parent == "Ladoix"
            and site.name == name
            and site.site_type == site_type
        )

    def origin(self, name: str, variant: str, grapes: dict[str, int]):
        site = self.site(name)
        return self.factory.create(
            OriginRequest(
                country="France",
                region=site.region,
                appellation="Ladoix",
                grapes=grapes,
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant=variant,
            )
        )

    def test_dual_color_climat_passes_for_both_colors(self):
        white = self.origin("Basses Mourottes", "white premier cru", {"Chardonnay": 100})
        red = self.origin("Basses Mourottes", "red premier cru", {"Pinot Noir": 100})
        self.assertTrue(white.site_claim_eligible)
        self.assertTrue(red.site_claim_eligible)
        self.assertEqual(
            white.site_claim_rule_id,
            "siteclaim:fr:ladoix:white-premier-cru-climat",
        )
        self.assertEqual(
            red.site_claim_rule_id,
            "siteclaim:fr:ladoix:red-premier-cru-climat",
        )

    def test_white_only_climat_blocks_red(self):
        white = self.origin("En Naget", "white premier cru", {"Chardonnay": 100})
        red = self.origin("En Naget", "red premier cru", {"Pinot Noir": 100})
        self.assertTrue(white.site_claim_eligible)
        self.assertFalse(red.site_claim_eligible)
        self.assertEqual(red.site_claim_status, "site_claim_rule_conditions_not_met")

    def test_red_only_climat_blocks_white(self):
        red = self.origin("Bois Roussot", "red premier cru", {"Pinot Noir": 100})
        white = self.origin("Bois Roussot", "white premier cru", {"Chardonnay": 100})
        self.assertTrue(red.site_claim_eligible)
        self.assertFalse(white.site_claim_eligible)
        self.assertEqual(white.site_claim_status, "site_claim_rule_conditions_not_met")

    def test_ladoix_lieu_dit_is_not_promoted(self):
        site = self.site("Bas de Naget", "lieu_dit")
        origin = self.factory.create(
            OriginRequest(
                country="France",
                region=site.region,
                appellation="Ladoix",
                grapes={"Chardonnay": 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant="white standard",
            )
        )
        self.assertFalse(origin.site_claim_eligible)
        self.assertEqual(origin.site_claim_status, "site_claim_rule_unverified")


class LadoixAuthoritativeCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = AuthoritativeCatalogGenerator()
        cls.items = cls.generator.generate(as_of_year=2026, include_site_claims=True)

    def sites(self, spec_id: str) -> set[str]:
        return {
            item.wine.vineyard
            for item in self.items
            if item.legal_spec_id == spec_id and item.wine.vineyard
        }

    def test_ladoix_catalog_matches_exact_color_matrix(self):
        white = self.sites("fr:ladoix:white-premier-cru")
        red = self.sites("fr:ladoix:red-premier-cru")
        self.assertEqual(len(white), 8)
        self.assertEqual(len(red), 8)
        self.assertEqual(len(white | red), 11)

        self.assertIn("En Naget", white)
        self.assertNotIn("En Naget", red)
        self.assertIn("Le Rognet et Corton", white)
        self.assertNotIn("Le Rognet et Corton", red)
        self.assertIn("Bois Roussot", red)
        self.assertNotIn("Bois Roussot", white)
        self.assertIn("Les Joyeuses", red)
        self.assertNotIn("Les Joyeuses", white)
        self.assertIn("Basses Mourottes", white & red)


if __name__ == "__main__":
    unittest.main()
