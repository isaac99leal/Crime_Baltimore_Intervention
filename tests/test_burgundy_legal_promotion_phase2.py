from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory


class BurgundyPhase2StrictSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_puligny_color_and_level_variants(self):
        expected = {
            "white standard": (11.0, 57.0, 3.0, None),
            "red standard": (10.5, 50.0, 2.0, 0.4),
            "white premier cru": (11.5, 55.0, 3.0, None),
            "red premier cru": (11.0, 48.0, 2.0, 0.4),
        }
        for variant, values in expected.items():
            spec = self.registry.resolve(
                country="France",
                appellation="Puligny-Montrachet",
                variant=variant,
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

    def test_volnay_standard_and_premier_cru(self):
        standard = self.registry.resolve(
            country="France", appellation="Volnay", variant="standard"
        )
        premier = self.registry.resolve(
            country="France", appellation="Volnay", variant="premier cru"
        )
        self.assertIsNotNone(standard)
        self.assertIsNotNone(premier)
        self.assertTrue(self.registry.evaluate_blend(standard, "Pinot Noir").eligible)
        self.assertFalse(self.registry.evaluate_blend(standard, "Chardonnay").eligible)
        self.assertEqual((standard.min_potential_alcohol_pct, standard.max_yield_hl_ha), (10.5, 50.0))
        self.assertEqual((premier.min_potential_alcohol_pct, premier.max_yield_hl_ha), (11.0, 48.0))
        self.assertEqual(standard.max_residual_sugar_g_l, 2.0)
        self.assertEqual(standard.max_malic_acid_g_l, 0.4)

    def test_saint_aubin_color_and_level_variants(self):
        expected = {
            "white standard": (11.0, 57.0, 3.0, None),
            "red standard": (10.5, 50.0, 2.0, 0.4),
            "white premier cru": (11.5, 55.0, 3.0, None),
            "red premier cru": (11.0, 48.0, 2.0, 0.4),
        }
        for variant, values in expected.items():
            spec = self.registry.resolve(
                country="France", appellation="Saint-Aubin", variant=variant
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


class BurgundyPhase2SiteClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()

    @classmethod
    def site(cls, name: str, site_type: str, parent: str):
        return next(
            site
            for site in cls.factory.catalog.named_sites
            if site.name == name
            and site.site_type == site_type
            and site.parent == parent
        )

    def test_puligny_white_premier_cru_climat_passes(self):
        site = self.site("Les Pucelles", "climat", "Puligny-Montrachet")
        origin = self.factory.create(
            OriginRequest(
                country="France",
                region=site.region,
                appellation="Puligny-Montrachet",
                grapes={"Chardonnay": 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant="white premier cru",
            )
        )
        self.assertTrue(origin.site_claim_eligible)
        self.assertEqual(
            origin.site_claim_rule_id,
            "siteclaim:fr:puligny-montrachet:white-premier-cru-climat",
        )

    def test_puligny_red_climat_uses_exact_color_matrix(self):
        dual = self.site("Les Pucelles", "climat", "Puligny-Montrachet")
        eligible = self.factory.create(
            OriginRequest(
                country="France",
                region=dual.region,
                appellation="Puligny-Montrachet",
                grapes={"Pinot Noir": 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=dual.id,
                wine_variant="red premier cru",
            )
        )
        self.assertTrue(eligible.site_claim_eligible)
        self.assertEqual(
            eligible.site_claim_rule_id,
            "siteclaim:fr:puligny-montrachet:red-premier-cru-climat",
        )

        white_only = self.site("Hameau de Blagny", "climat", "Puligny-Montrachet")
        blocked = self.factory.create(
            OriginRequest(
                country="France",
                region=white_only.region,
                appellation="Puligny-Montrachet",
                grapes={"Pinot Noir": 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=white_only.id,
                wine_variant="red premier cru",
            )
        )
        self.assertFalse(blocked.site_claim_eligible)
        self.assertEqual(blocked.site_claim_status, "site_claim_rule_conditions_not_met")

    def test_volnay_premier_cru_climat_passes(self):
        site = self.site("Clos des Chênes", "climat", "Volnay")
        origin = self.factory.create(
            OriginRequest(
                country="France",
                region=site.region,
                appellation="Volnay",
                grapes={"Pinot Noir": 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant="premier cru",
            )
        )
        self.assertTrue(origin.site_claim_eligible)
        self.assertEqual(
            origin.site_claim_rule_id,
            "siteclaim:fr:volnay:premier-cru-climat",
        )

    def test_saint_aubin_climat_passes_for_both_colors(self):
        site = self.site("En Remilly", "climat", "Saint-Aubin")
        for variant, grapes in (
            ("white premier cru", {"Chardonnay": 100}),
            ("red premier cru", {"Pinot Noir": 100}),
        ):
            origin = self.factory.create(
                OriginRequest(
                    country="France",
                    region=site.region,
                    appellation="Saint-Aubin",
                    grapes=grapes,
                    vintage_year=2025,
                    label_scope="regulated_gi",
                    site_id=site.id,
                    wine_variant=variant,
                )
            )
            self.assertTrue(origin.site_claim_eligible, variant)
            self.assertEqual(
                origin.site_claim_rule_id,
                "siteclaim:fr:saint-aubin:premier-cru-climat",
            )

    def test_generic_lieux_dits_stay_fail_closed(self):
        cases = (
            ("Puligny-Montrachet", "Les Enseignères", "white standard", {"Chardonnay": 100}),
            ("Volnay", "Les Serpens", "standard", {"Pinot Noir": 100}),
            ("Saint-Aubin", "Gamay", "white standard", {"Chardonnay": 100}),
        )
        for parent, name, variant, grapes in cases:
            site = self.site(name, "lieu_dit", parent)
            origin = self.factory.create(
                OriginRequest(
                    country="France",
                    region=site.region,
                    appellation=parent,
                    grapes=grapes,
                    vintage_year=2025,
                    label_scope="regulated_gi",
                    site_id=site.id,
                    wine_variant=variant,
                )
            )
            self.assertFalse(origin.site_claim_eligible, (parent, name))
            self.assertEqual(origin.site_claim_status, "site_claim_rule_unverified")


class BurgundyPhase2AuthoritativeCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = AuthoritativeCatalogGenerator()
        cls.items = cls.generator.generate(as_of_year=2026, include_site_claims=True)

    def unique_sites_for(self, spec_id: str) -> set[str]:
        return {
            item.wine.vineyard
            for item in self.items
            if item.legal_spec_id == spec_id and item.wine.vineyard
        }

    def test_catalog_contains_exact_puligny_premier_cru_color_matrix(self):
        white = self.unique_sites_for("fr:puligny-montrachet:white-premier-cru")
        red = self.unique_sites_for("fr:puligny-montrachet:red-premier-cru")
        self.assertEqual(len(white), 17)
        self.assertEqual(len(red), 14)
        self.assertIn("Les Pucelles", white)
        self.assertIn("Les Pucelles", red)
        for name in ("Hameau de Blagny", "La Garenne", "Sous le Puits"):
            self.assertIn(name, white)
            self.assertNotIn(name, red)

    def test_catalog_contains_all_seeded_volnay_premier_cru_climats(self):
        sites = self.unique_sites_for("fr:volnay:premier-cru")
        self.assertEqual(len(sites), 29)
        self.assertIn("Clos des Chênes", sites)
        self.assertIn("Champans", sites)

    def test_catalog_contains_all_seeded_saint_aubin_climats_for_both_colors(self):
        white = self.unique_sites_for("fr:saint-aubin:white-premier-cru")
        red = self.unique_sites_for("fr:saint-aubin:red-premier-cru")
        self.assertEqual(len(white), 30)
        self.assertEqual(len(red), 30)
        self.assertIn("En Remilly", white)
        self.assertIn("En Remilly", red)


if __name__ == "__main__":
    unittest.main()
