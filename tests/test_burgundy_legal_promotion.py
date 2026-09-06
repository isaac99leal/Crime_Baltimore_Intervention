from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.generation import (
    ConstrainedWineBuilder,
    WineBuildRequest,
    WineProductionConstraintError,
    WineReleaseConstraintError,
)
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory
from sommelier_v2.knowledge.site_claims import SiteClaimRegistry


class BurgundyStrictSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_meursault_variants_are_strictly_resolved(self):
        expected = {
            "white standard": (11.0, 57.0),
            "red standard": (10.5, 50.0),
            "white premier cru": (11.5, 55.0),
            "red premier cru": (11.0, 48.0),
        }
        for variant, (minimum_alcohol, max_yield) in expected.items():
            spec = self.registry.resolve(
                country="France",
                appellation="Meursault",
                variant=variant,
            )
            self.assertIsNotNone(spec)
            self.assertEqual(spec.min_potential_alcohol_pct, minimum_alcohol)
            self.assertEqual(spec.max_yield_hl_ha, max_yield)

    def test_chambolle_standard_and_premier_cru_are_pinot_noir_positive_paths(self):
        standard = self.registry.resolve(
            country="France",
            appellation="Chambolle-Musigny",
            variant="standard",
        )
        premier = self.registry.resolve(
            country="France",
            appellation="Chambolle-Musigny",
            variant="premier cru",
        )
        self.assertIsNotNone(standard)
        self.assertIsNotNone(premier)
        self.assertTrue(self.registry.evaluate_blend(standard, "Pinot Noir").eligible)
        self.assertTrue(self.registry.evaluate_blend(premier, "Pinot Noir").eligible)
        self.assertFalse(self.registry.evaluate_blend(premier, "Chardonnay").eligible)
        self.assertEqual(standard.max_yield_hl_ha, 50.0)
        self.assertEqual(premier.max_yield_hl_ha, 48.0)

    def test_complete_production_requires_and_enforces_wine_yield(self):
        spec = self.registry.resolve(
            country="France",
            appellation="Meursault",
            variant="white standard",
        )
        missing = self.registry.validate_production(
            spec,
            potential_alcohol_pct=11.5,
            require_complete=True,
        )
        excessive = self.registry.validate_production(
            spec,
            wine_yield_hl_ha=57.1,
            potential_alcohol_pct=11.5,
            require_complete=True,
        )
        good = self.registry.validate_production(
            spec,
            wine_yield_hl_ha=55.0,
            potential_alcohol_pct=11.5,
            require_complete=True,
        )
        self.assertFalse(missing.eligible)
        self.assertFalse(excessive.eligible)
        self.assertTrue(good.eligible)

    def test_meursault_white_conservative_sugar_ceiling_is_executable(self):
        spec = self.registry.resolve(
            country="France",
            appellation="Meursault",
            variant="white standard",
        )
        good = self.registry.validate_release(
            spec,
            total_aging_months=0,
            residual_sugar_g_l=3.0,
            vintage_year=2025,
            release_year=2026,
            require_complete=True,
        )
        high = self.registry.validate_release(
            spec,
            total_aging_months=0,
            residual_sugar_g_l=3.1,
            vintage_year=2025,
            release_year=2026,
            require_complete=True,
        )
        self.assertTrue(good.eligible)
        self.assertFalse(high.eligible)

    def test_chambolle_sugar_and_malic_limits_are_executable(self):
        spec = self.registry.resolve(
            country="France",
            appellation="Chambolle-Musigny",
            variant="premier cru",
        )
        release_evidence = dict(
            total_aging_months=0,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=1.8,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        good = self.registry.validate_release(
            spec,
            malic_acid_g_l=0.3,
            **release_evidence,
        )
        bad_malic = self.registry.validate_release(
            spec,
            malic_acid_g_l=0.41,
            **release_evidence,
        )
        self.assertTrue(good.eligible)
        self.assertFalse(bad_malic.eligible)


class BurgundySiteClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()
        cls.claims = SiteClaimRegistry()

    @classmethod
    def site(cls, name: str, site_type: str, parent: str):
        return next(
            site
            for site in cls.factory.catalog.named_sites
            if site.name == name and site.site_type == site_type and site.parent == parent
        )

    def test_meursault_white_premier_cru_climat_claim_passes(self):
        site = self.site("Perrières", "climat", "Meursault")
        origin = self.factory.create(
            OriginRequest(
                country="France",
                region=site.region,
                appellation="Meursault",
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
            "siteclaim:fr:meursault:white-premier-cru-climat",
        )

    def test_chambolle_premier_cru_climat_claim_passes(self):
        site = self.site("Les Amoureuses", "climat", "Chambolle-Musigny")
        origin = self.factory.create(
            OriginRequest(
                country="France",
                region=site.region,
                appellation="Chambolle-Musigny",
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
            "siteclaim:fr:chambolle-musigny:premier-cru-climat",
        )

    def test_meursault_generic_lieu_dit_remains_fail_closed(self):
        site = self.site("Les Narvaux Dessus", "lieu_dit", "Meursault")
        origin = self.factory.create(
            OriginRequest(
                country="France",
                region=site.region,
                appellation="Meursault",
                grapes={"Chardonnay": 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant="white standard",
            )
        )
        self.assertFalse(origin.site_claim_eligible)
        self.assertEqual(origin.site_claim_status, "site_claim_rule_unverified")


class BurgundyBuilderAndCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()
        cls.builder = ConstrainedWineBuilder(origin_factory=cls.factory)
        cls.generator = AuthoritativeCatalogGenerator(catalog=cls.factory.catalog)
        cls.amoureuses = next(
            site
            for site in cls.factory.catalog.named_sites
            if site.name == "Les Amoureuses"
            and site.site_type == "climat"
            and site.parent == "Chambolle-Musigny"
        )

    def chambolle_request(self, **changes):
        values = dict(
            id="strict:test:chambolle",
            producer="Simulation Producer Burgundy",
            label="Chambolle-Musigny Premier Cru · Les Amoureuses",
            origin=OriginRequest(
                country="France",
                region=self.amoureuses.region,
                appellation="Chambolle-Musigny",
                grapes={"Pinot Noir": 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=self.amoureuses.id,
                wine_variant="premier cru",
            ),
            alcohol=13.0,
            wine_yield_hl_ha=45.0,
            must_sugar_g_l=189.0,
            potential_alcohol_pct=11.8,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=1.5,
            malic_acid_g_l=0.3,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
        )
        values.update(changes)
        return WineBuildRequest(**values)

    def test_builder_requires_hl_yield(self):
        with self.assertRaises(WineProductionConstraintError):
            self.builder.build(self.chambolle_request(wine_yield_hl_ha=None))

    def test_builder_rejects_malic_limit(self):
        with self.assertRaises(WineReleaseConstraintError):
            self.builder.build(self.chambolle_request(malic_acid_g_l=0.5))

    def test_builder_emits_verified_chambolle_climat(self):
        result = self.builder.build(self.chambolle_request())
        self.assertEqual(result.wine.vineyard, "Les Amoureuses")
        self.assertEqual(result.evidence.legal_spec_id, "fr:chambolle-musigny:premier-cru")
        self.assertTrue(result.evidence.site_claim_eligible)

    def test_authoritative_catalog_contains_promoted_burgundy_climats(self):
        items = self.generator.generate(as_of_year=2026, include_site_claims=True)
        self.assertTrue(
            any(
                item.legal_spec_id == "fr:chambolle-musigny:premier-cru"
                and item.wine.vineyard == "Les Amoureuses"
                for item in items
            )
        )
        self.assertTrue(
            any(
                item.legal_spec_id == "fr:meursault:white-premier-cru"
                and item.wine.vineyard == "Perrières"
                for item in items
            )
        )


if __name__ == "__main__":
    unittest.main()
