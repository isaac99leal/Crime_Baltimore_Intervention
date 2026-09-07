from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory


EXPECTED_CLIMATS = {
    "Hameau de Blagny",
    "La Garenne ou sur la Garenne",
    "La Jeunellotte",
    "La Pièce sous le Bois",
    "Sous Blagny",
    "Sous le Dos d’Ane",
    "Sous le Puits",
}


class BlagnyLegalSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_standard_and_premier_cru_exact_limits(self):
        expected = {
            "standard": ("fr:blagny:standard", 180.0, 10.5, 50.0, 13.5),
            "premier cru": ("fr:blagny:premier-cru", 189.0, 11.0, 48.0, 14.0),
        }
        for variant, (spec_id, sugar, alcohol, yield_hl, total_alcohol) in expected.items():
            spec = self.registry.resolve(country="France", appellation="Blagny", variant=variant)
            self.assertIsNotNone(spec, variant)
            self.assertEqual(spec.id, spec_id)
            self.assertEqual(spec.wine_style, "red")
            self.assertEqual(spec.min_must_sugar_g_l, sugar)
            self.assertEqual(spec.min_potential_alcohol_pct, alcohol)
            self.assertEqual(spec.max_yield_hl_ha, yield_hl)
            self.assertEqual(spec.max_total_alcohol_pct, total_alcohol)
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

    def test_positive_blend_path_is_pinot_noir_only(self):
        for variant in ("standard", "premier cru"):
            spec = self.registry.resolve(country="France", appellation="Blagny", variant=variant)
            self.assertIsNotNone(spec)
            self.assertTrue(self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible)
            for grape in ("Chardonnay", "Pinot Blanc", "Pinot Gris", "César"):
                self.assertFalse(self.registry.evaluate_blend(spec, {grape: 100}).eligible)
            self.assertFalse(
                self.registry.evaluate_blend(spec, {"Pinot Noir": 85, "Chardonnay": 15}).eligible
            )
            self.assertFalse(
                self.registry.evaluate_blend(spec, {"Pinot Noir": 85, "César": 15}).eligible
            )

    def test_release_malic_and_sugar_limits_fail_closed(self):
        spec = self.registry.resolve(country="France", appellation="Blagny", variant="premier cru")
        self.assertIsNotNone(spec)
        valid = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=2.0,
            malic_acid_g_l=0.4,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        early = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=2.0,
            malic_acid_g_l=0.4,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=29,
            require_complete=True,
        )
        sugar_fail = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=2.01,
            malic_acid_g_l=0.4,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        malic_fail = self.registry.validate_release(
            spec,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=2.0,
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
        self.assertTrue(valid.eligible)
        self.assertFalse(early.eligible)
        self.assertFalse(sugar_fail.eligible)
        self.assertFalse(malic_fail.eligible)


class BlagnySiteClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()
        cls.catalog = cls.factory.catalog

    def test_exact_seven_parent_scoped_climats(self):
        sites = [
            site for site in self.catalog.named_sites
            if site.parent == "Blagny"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        ]
        self.assertEqual({site.name for site in sites}, EXPECTED_CLIMATS)
        self.assertEqual(len(sites), 7)
        self.assertTrue(all("blagny_cahier_2026" in site.source_ids for site in sites))

    def test_all_seven_premier_cru_claims_pass(self):
        for site in self.catalog.named_sites:
            if site.parent != "Blagny" or site.name not in EXPECTED_CLIMATS:
                continue
            origin = self.factory.create(OriginRequest(
                country="France",
                region="Bourgogne",
                appellation="Blagny",
                grapes={"Pinot Noir": 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant="premier cru",
            ))
            self.assertTrue(origin.site_claim_eligible, site.name)

    def test_same_named_puligny_site_does_not_substitute_for_blagny_parent(self):
        puligny = next(
            site for site in self.catalog.named_sites
            if site.parent == "Puligny-Montrachet" and site.name == "Hameau de Blagny"
        )
        origin = self.factory.create(OriginRequest(
            country="France",
            region="Bourgogne",
            appellation="Blagny",
            grapes={"Pinot Noir": 100},
            vintage_year=2025,
            label_scope="regulated_gi",
            site_id=puligny.id,
            wine_variant="premier cru",
        ))
        self.assertFalse(origin.site_claim_eligible)

    def test_standard_blagny_does_not_inherit_premier_cru_site_claim(self):
        site = next(
            site for site in self.catalog.named_sites
            if site.parent == "Blagny" and site.name == "Sous le Puits"
        )
        origin = self.factory.create(OriginRequest(
            country="France",
            region="Bourgogne",
            appellation="Blagny",
            grapes={"Pinot Noir": 100},
            vintage_year=2025,
            label_scope="regulated_gi",
            site_id=site.id,
            wine_variant="standard",
        ))
        self.assertFalse(origin.site_claim_eligible)


class BlagnyAuthoritativeCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = AuthoritativeCatalogGenerator().generate(
            as_of_year=2026, include_site_claims=True
        )

    def test_standard_is_site_free_and_premier_cru_has_all_seven_sites(self):
        standard = [item for item in self.items if item.legal_spec_id == "fr:blagny:standard"]
        premier = [item for item in self.items if item.legal_spec_id == "fr:blagny:premier-cru"]
        self.assertEqual(len(standard), 1)
        self.assertTrue(all(not item.wine.vineyard for item in standard))
        self.assertEqual(len(premier), 8)
        site_rows = [item for item in premier if item.wine.vineyard]
        self.assertEqual(len(site_rows), 7)
        self.assertEqual({item.wine.vineyard for item in site_rows}, EXPECTED_CLIMATS)


if __name__ == "__main__":
    unittest.main()
