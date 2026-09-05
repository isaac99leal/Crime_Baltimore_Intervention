from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory
from sommelier_v2.knowledge.site_claims import SiteClaimRegistry


OFFICIAL_CLIMATS = {
    "Blanchot",
    "Bougros",
    "Grenouilles",
    "Les Clos",
    "Preuses",
    "Valmur",
    "Vaudésir",
}


class ChablisGrandCruLegalSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_current_2024_spec_supersedes_2011_framework(self):
        spec = self.registry.resolve(
            country="France", appellation="Chablis grand cru", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        self.assertEqual(spec.id, "fr:chablis-grand-cru:grand-cru")
        self.assertEqual(spec.effective_from, "2024-11-10")
        self.assertEqual(spec.wine_style, "white")
        self.assertEqual(spec.allowed_grapes, ("Chardonnay",))
        self.assertEqual(spec.min_must_sugar_g_l, 178.0)
        self.assertEqual(spec.min_potential_alcohol_pct, 11.0)
        self.assertEqual(spec.max_yield_hl_ha, 54.0)
        self.assertEqual(spec.max_total_alcohol_pct, 13.5)
        self.assertEqual(spec.max_residual_sugar_g_l, 3.0)
        self.assertEqual(
            (
                spec.min_elevage_year_offset,
                spec.min_elevage_until_month,
                spec.min_elevage_until_day,
            ),
            (1, 3, 15),
        )
        self.assertEqual(
            (
                spec.release_year_offset,
                spec.earliest_release_month,
                spec.earliest_release_day,
            ),
            (1, 3, 31),
        )

    def test_chardonnay_only_composition_is_enforced(self):
        spec = self.registry.resolve(
            country="France", appellation="Chablis Grand Cru", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        self.assertTrue(
            self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(spec, {"Pinot Blanc": 100}).eligible
        )

    def test_maturity_yield_and_total_alcohol_are_executable(self):
        spec = self.registry.resolve(
            country="France", appellation="Chablis grand cru", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        self.assertTrue(
            self.registry.validate_production(
                spec,
                wine_yield_hl_ha=54.0,
                must_sugar_g_l=178.0,
                potential_alcohol_pct=11.0,
                require_complete=True,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                spec,
                wine_yield_hl_ha=54.01,
                must_sugar_g_l=178.0,
                potential_alcohol_pct=11.0,
                require_complete=True,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                spec,
                wine_yield_hl_ha=54.0,
                must_sugar_g_l=177.9,
                potential_alcohol_pct=11.0,
                require_complete=True,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_release(
                spec,
                total_aging_months=0,
                total_alcohol_pct=13.51,
                residual_sugar_g_l=2.0,
                vintage_year=2025,
                elevage_end_year=2026,
                elevage_end_month=3,
                elevage_end_day=15,
                release_year=2026,
                release_month=3,
                release_day=31,
                require_complete=True,
            ).eligible
        )

    def test_exact_march_calendar_gates_are_enforced(self):
        spec = self.registry.resolve(
            country="France", appellation="Chablis grand cru", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        early_elevage = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=13.0,
            residual_sugar_g_l=2.0,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=3,
            elevage_end_day=14,
            release_year=2026,
            release_month=3,
            release_day=31,
            require_complete=True,
        )
        early_release = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=13.0,
            residual_sugar_g_l=2.0,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=3,
            elevage_end_day=15,
            release_year=2026,
            release_month=3,
            release_day=30,
            require_complete=True,
        )
        exact = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=13.0,
            residual_sugar_g_l=2.0,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=3,
            elevage_end_day=15,
            release_year=2026,
            release_month=3,
            release_day=31,
            require_complete=True,
        )
        self.assertFalse(early_elevage.eligible)
        self.assertFalse(early_release.eligible)
        self.assertTrue(exact.eligible)


class ChablisGrandCruSiteClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()
        cls.claims = SiteClaimRegistry()
        cls.official = [
            site
            for site in cls.factory.catalog.named_sites
            if site.parent == "Chablis grand cru" and site.site_type == "climat"
        ]
        cls.moutonne = next(
            site
            for site in cls.factory.catalog.named_sites
            if site.parent == "Chablis grand cru" and site.name == "La Moutonne"
        )

    def test_exact_seven_official_climats_are_loaded(self):
        self.assertEqual(len(self.official), 7)
        self.assertEqual({site.name for site in self.official}, OFFICIAL_CLIMATS)
        self.assertTrue(
            all(site.legal_status == "official_appellation_climat" for site in self.official)
        )

    def test_official_climat_passes_strict_claim_rule(self):
        site = next(site for site in self.official if site.name == "Les Clos")
        origin = self.factory.create(
            OriginRequest(
                country="France",
                region="Chablis",
                appellation="Chablis grand cru",
                grapes={"Chardonnay": 100},
                vintage_year=2024,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant="grand cru",
            )
        )
        self.assertTrue(origin.site_claim_eligible)
        self.assertEqual(
            origin.site_claim_rule_id,
            "siteclaim:fr:chablis-grand-cru:official-climat",
        )

    def test_la_moutonne_remains_identity_only_and_fail_closed(self):
        self.assertEqual(self.moutonne.site_type, "usage_name")
        self.assertEqual(self.moutonne.legal_status, "historical_usage_name")
        origin = self.factory.create(
            OriginRequest(
                country="France",
                region="Chablis",
                appellation="Chablis grand cru",
                grapes={"Chardonnay": 100},
                vintage_year=2024,
                label_scope="regulated_gi",
                site_id=self.moutonne.id,
                wine_variant="grand cru",
            )
        )
        self.assertFalse(origin.site_claim_eligible)
        self.assertEqual(origin.site_claim_status, "site_claim_rule_unverified")


class ChablisGrandCruCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = AuthoritativeCatalogGenerator().generate(
            as_of_year=2026, include_site_claims=True
        )

    def test_catalog_has_one_base_plus_seven_official_climats(self):
        rows = [
            item
            for item in self.items
            if item.legal_spec_id == "fr:chablis-grand-cru:grand-cru"
        ]
        self.assertEqual(len(rows), 8)
        base = [item for item in rows if not item.wine.vineyard]
        sites = [item for item in rows if item.wine.vineyard]
        self.assertEqual(len(base), 1)
        self.assertEqual(len(sites), 7)
        self.assertEqual({item.wine.vineyard for item in sites}, OFFICIAL_CLIMATS)
        self.assertEqual(base[0].wine.grapes, ("Chardonnay",))

    def test_la_moutonne_is_not_emitted_as_an_official_climat_claim(self):
        leaked = [
            item
            for item in self.items
            if item.legal_spec_id == "fr:chablis-grand-cru:grand-cru"
            and item.wine.vineyard == "La Moutonne"
        ]
        self.assertFalse(leaked)


if __name__ == "__main__":
    unittest.main()
