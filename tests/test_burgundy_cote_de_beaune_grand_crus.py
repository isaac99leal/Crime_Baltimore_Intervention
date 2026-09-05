from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory
from sommelier_v2.knowledge.site_claims import SiteClaimRegistry


CORTON_CLIMATS = {
    "Basses Mourottes",
    "Clos des Meix",
    "Hautes Mourottes",
    "La Toppe au Vert",
    "La Vigne au Saint",
    "Le Clos du Roi",
    "Le Corton",
    "Le Meix Lallemand",
    "Le Rognet et Corton",
    "Les Bressandes",
    "Les Carrières",
    "Les Chaumes",
    "Les Combes",
    "Les Fiètres",
    "Les Grandes Lolières",
    "Les Grèves",
    "Les Languettes",
    "Les Maréchaudes",
    "Les Moutottes",
    "Les Paulands",
    "Les Perrières",
    "Les Pougets",
    "Les Renardes",
    "Les Vergennes",
}


class CoteDeBeauneGrandCruLegalSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_corton_has_separate_red_and_white_strict_paths(self):
        red = self.registry.resolve(
            country="France", appellation="Corton", variant="red grand cru"
        )
        white = self.registry.resolve(
            country="France", appellation="Corton", variant="white grand cru"
        )
        self.assertIsNotNone(red)
        self.assertIsNotNone(white)
        self.assertNotEqual(red.id, white.id)

        self.assertEqual(red.allowed_grapes, ("Pinot Noir",))
        self.assertEqual(red.min_must_sugar_g_l, 198.0)
        self.assertEqual(red.min_potential_alcohol_pct, 11.5)
        self.assertEqual(red.max_yield_hl_ha, 42.0)
        self.assertEqual(red.max_residual_sugar_g_l, 2.0)
        self.assertEqual(red.max_malic_acid_g_l, 0.4)

        self.assertEqual(white.allowed_grapes, ("Chardonnay", "Pinot Blanc"))
        self.assertEqual(white.min_must_sugar_g_l, 195.0)
        self.assertEqual(white.min_potential_alcohol_pct, 12.0)
        self.assertEqual(white.max_yield_hl_ha, 48.0)
        self.assertEqual(white.max_residual_sugar_g_l, 3.0)
        self.assertIsNone(white.max_malic_acid_g_l)
        self.assertEqual(red.max_total_alcohol_pct, 14.5)
        self.assertEqual(white.max_total_alcohol_pct, 14.5)

    def test_corton_white_blend_caps_pinot_blanc_at_30_percent(self):
        spec = self.registry.resolve(
            country="France", appellation="Corton", variant="white grand cru"
        )
        self.assertIsNotNone(spec)
        self.assertTrue(
            self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible
        )
        self.assertTrue(
            self.registry.evaluate_blend(
                spec, {"Chardonnay": 70, "Pinot Blanc": 30}
            ).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(
                spec, {"Chardonnay": 69, "Pinot Blanc": 31}
            ).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(spec, {"Pinot Blanc": 100}).eligible
        )

    def test_corton_red_does_not_turn_accessory_grapes_into_cellar_blends(self):
        spec = self.registry.resolve(
            country="France", appellation="Corton", variant="red grand cru"
        )
        self.assertIsNotNone(spec)
        self.assertTrue(
            self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(spec, {"Pinot Blanc": 100}).eligible
        )

    def test_corton_charlemagne_has_its_own_white_grand_cru_origin(self):
        spec = self.registry.resolve(
            country="France", appellation="Corton-Charlemagne", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        self.assertEqual(spec.id, "fr:corton-charlemagne:grand-cru")
        self.assertEqual(spec.wine_style, "white")
        self.assertEqual(spec.min_must_sugar_g_l, 195.0)
        self.assertEqual(spec.min_potential_alcohol_pct, 12.0)
        self.assertEqual(spec.max_yield_hl_ha, 48.0)
        self.assertTrue(
            self.registry.evaluate_blend(
                spec, {"Chardonnay": 70, "Pinot Blanc": 30}
            ).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(
                spec, {"Chardonnay": 69, "Pinot Blanc": 31}
            ).eligible
        )

    def test_montrachet_is_strict_chardonnay(self):
        spec = self.registry.resolve(
            country="France", appellation="Montrachet", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        self.assertEqual(spec.id, "fr:montrachet:grand-cru")
        self.assertEqual(spec.allowed_grapes, ("Chardonnay",))
        self.assertEqual(spec.min_must_sugar_g_l, 195.0)
        self.assertEqual(spec.min_potential_alcohol_pct, 12.0)
        self.assertEqual(spec.max_yield_hl_ha, 48.0)
        self.assertTrue(
            self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(spec, {"Pinot Blanc": 100}).eligible
        )

    def test_exact_elevage_and_release_dates_apply(self):
        spec = self.registry.resolve(
            country="France", appellation="Montrachet", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        early_elevage = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=2.0,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=14,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        early_release = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=14.0,
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
        exact = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=2.0,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        self.assertFalse(early_elevage.eligible)
        self.assertFalse(early_release.eligible)
        self.assertTrue(exact.eligible)


class CortonGrandCruSiteClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()
        cls.claims = SiteClaimRegistry()
        cls.sites = [
            site
            for site in cls.factory.catalog.named_sites
            if site.parent == "Corton" and site.site_type == "climat"
        ]

    def test_site_claim_registry_discovers_new_regional_rule_file(self):
        rule = next(
            (
                rule
                for rule in self.claims.rules
                if rule.id == "siteclaim:fr:corton:grand-cru-climat:red"
            ),
            None,
        )
        self.assertIsNotNone(rule)
        self.assertEqual(rule.allowed_wine_variants, ("red grand cru",))

    def test_all_24_official_corton_climats_are_ingested(self):
        self.assertEqual(len(self.sites), 24)
        self.assertEqual({site.name for site in self.sites}, CORTON_CLIMATS)
        self.assertTrue(
            all(site.legal_status == "official_appellation_climat" for site in self.sites)
        )

    def test_corton_climat_claim_is_red_only(self):
        site = next(site for site in self.sites if site.name == "Le Clos du Roi")
        red = self.factory.create(
            OriginRequest(
                country="France",
                region="Bourgogne",
                appellation="Corton",
                grapes={"Pinot Noir": 100},
                vintage_year=2024,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant="red grand cru",
            )
        )
        white = self.factory.create(
            OriginRequest(
                country="France",
                region="Bourgogne",
                appellation="Corton",
                grapes={"Chardonnay": 100},
                vintage_year=2024,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant="white grand cru",
            )
        )
        self.assertTrue(red.site_claim_eligible)
        self.assertEqual(
            red.site_claim_rule_id, "siteclaim:fr:corton:grand-cru-climat:red"
        )
        self.assertFalse(white.site_claim_eligible)
        self.assertEqual(white.site_claim_status, "site_claim_rule_conditions_not_met")


class CoteDeBeauneGrandCruCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = AuthoritativeCatalogGenerator().generate(
            as_of_year=2026, include_site_claims=True
        )

    def test_red_corton_generates_base_plus_exactly_24_climats(self):
        rows = [
            item
            for item in self.items
            if item.legal_spec_id == "fr:corton:red-grand-cru"
        ]
        self.assertEqual(len(rows), 25)
        base = [item for item in rows if not item.wine.vineyard]
        sites = [item for item in rows if item.wine.vineyard]
        self.assertEqual(len(base), 1)
        self.assertEqual(len(sites), 24)
        self.assertEqual({item.wine.vineyard for item in sites}, CORTON_CLIMATS)

    def test_white_corton_remains_base_only(self):
        rows = [
            item
            for item in self.items
            if item.legal_spec_id == "fr:corton:white-grand-cru"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].wine.vineyard, "")
        self.assertEqual(rows[0].wine.grapes, ("Chardonnay",))

    def test_corton_charlemagne_and_montrachet_are_separate_base_origins(self):
        for spec_id, appellation in (
            ("fr:corton-charlemagne:grand-cru", "Corton-Charlemagne"),
            ("fr:montrachet:grand-cru", "Montrachet"),
        ):
            rows = [item for item in self.items if item.legal_spec_id == spec_id]
            self.assertEqual(len(rows), 1, (spec_id, len(rows)))
            self.assertEqual(rows[0].wine.appellation, appellation)
            self.assertEqual(rows[0].wine.vineyard, "")


if __name__ == "__main__":
    unittest.main()
