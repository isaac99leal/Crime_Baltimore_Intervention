from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory


EXPECTED_RULLY_SPECS = {
    "white standard": ("fr:rully:white-standard", 178.0, 11.0, 50.0, 13.5, 3.0, None),
    "red standard": ("fr:rully:red-standard", 180.0, 10.5, 50.0, 13.5, 2.0, 0.4),
    "white premier cru": ("fr:rully:white-premier-cru", 187.0, 11.5, 46.0, 14.0, 3.0, None),
    "red premier cru": ("fr:rully:red-premier-cru", 189.0, 11.0, 46.0, 14.0, 2.0, 0.4),
}

EXPECTED_CORTON_SUFFIXES = {
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

HANDOFF_FALSE_POSITIVE_CORTON_SUFFIXES = {
    "En Charlemagne",
    "Le Charlemagne",
    "Les Chaumes et la Voierosse",
    "Les Meix",
}


class RullyStrictSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_four_color_level_paths_resolve_with_exact_limits(self):
        for variant, expected in EXPECTED_RULLY_SPECS.items():
            spec_id, sugar, natural_alcohol, yield_hl, total_alcohol, rs, malic = expected
            spec = self.registry.resolve(country="France", appellation="Rully", variant=variant)
            self.assertIsNotNone(spec, variant)
            self.assertEqual(spec.id, spec_id)
            self.assertEqual(spec.min_must_sugar_g_l, sugar)
            self.assertEqual(spec.min_potential_alcohol_pct, natural_alcohol)
            self.assertEqual(spec.max_yield_hl_ha, yield_hl)
            self.assertEqual(spec.max_total_alcohol_pct, total_alcohol)
            self.assertEqual(spec.max_residual_sugar_g_l, rs)
            self.assertEqual(spec.max_malic_acid_g_l, malic)
            self.assertEqual(
                (spec.min_elevage_year_offset, spec.min_elevage_until_month, spec.min_elevage_until_day),
                (1, 4, 1),
            )
            self.assertEqual(
                (spec.release_year_offset, spec.earliest_release_month, spec.earliest_release_day),
                (1, 4, 15),
            )

    def test_white_pinot_gris_is_a_standalone_positive_path(self):
        for variant in ("white standard", "white premier cru"):
            spec = self.registry.resolve(country="France", appellation="Rully", variant=variant)
            self.assertIsNotNone(spec)
            self.assertTrue(self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible)
            self.assertTrue(self.registry.evaluate_blend(spec, {"Pinot Gris": 100}).eligible)
            self.assertFalse(self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible)

    def test_red_accessory_white_grapes_are_not_promoted_as_cellar_blends(self):
        for variant in ("red standard", "red premier cru"):
            spec = self.registry.resolve(country="France", appellation="Rully", variant=variant)
            self.assertIsNotNone(spec)
            self.assertTrue(self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible)
            self.assertFalse(self.registry.evaluate_blend(spec, {"Chardonnay": 15, "Pinot Noir": 85}).eligible)
            self.assertFalse(self.registry.evaluate_blend(spec, {"Pinot Gris": 15, "Pinot Noir": 85}).eligible)

    def test_exact_elevage_release_and_red_malic_limits_are_enforced(self):
        white = self.registry.resolve(country="France", appellation="Rully", variant="white premier cru")
        red = self.registry.resolve(country="France", appellation="Rully", variant="red premier cru")
        self.assertIsNotNone(white)
        self.assertIsNotNone(red)

        white_ok = self.registry.validate_release(
            white,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=2.0,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=4,
            elevage_end_day=1,
            release_year=2026,
            release_month=4,
            release_day=15,
            require_complete=True,
        )
        early_release = self.registry.validate_release(
            white,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=2.0,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=4,
            elevage_end_day=1,
            release_year=2026,
            release_month=4,
            release_day=14,
            require_complete=True,
        )
        red_malic_fail = self.registry.validate_release(
            red,
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.41,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=4,
            elevage_end_day=1,
            release_year=2026,
            release_month=4,
            release_day=15,
            require_complete=True,
        )
        self.assertTrue(white_ok.eligible)
        self.assertFalse(early_release.eligible)
        self.assertFalse(red_malic_fail.eligible)


class RullySiteClaimAndCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()
        cls.generator = AuthoritativeCatalogGenerator(catalog=cls.factory.catalog)
        cls.items = cls.generator.generate(as_of_year=2026, include_site_claims=True)

    @classmethod
    def site(cls, name: str, site_type: str):
        return next(
            site for site in cls.factory.catalog.named_sites
            if site.parent == "Rully" and site.name == name and site.site_type == site_type
        )

    def test_exactly_23_rully_premier_cru_climat_identities(self):
        sites = [
            site for site in self.factory.catalog.named_sites
            if site.parent == "Rully"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        ]
        self.assertEqual(len(sites), 23)
        self.assertEqual(len({site.name for site in sites}), 23)
        self.assertTrue(all("bivb_rully" in site.source_ids for site in sites))

    def test_premier_cru_climat_claim_passes_for_both_colors(self):
        site = self.site("La Pucelle", "climat")
        for variant, grapes in (
            ("white premier cru", {"Chardonnay": 100}),
            ("white premier cru", {"Pinot Gris": 100}),
            ("red premier cru", {"Pinot Noir": 100}),
        ):
            origin = self.factory.create(OriginRequest(
                country="France",
                region=site.region,
                appellation="Rully",
                grapes=grapes,
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant=variant,
            ))
            self.assertTrue(origin.site_claim_eligible, (variant, grapes))

    def test_generic_rully_lieu_dit_remains_fail_closed(self):
        site = self.site("Bas de Vauvery", "lieu_dit")
        origin = self.factory.create(OriginRequest(
            country="France",
            region=site.region,
            appellation="Rully",
            grapes={"Chardonnay": 100},
            vintage_year=2025,
            label_scope="regulated_gi",
            site_id=site.id,
            wine_variant="white standard",
        ))
        self.assertFalse(origin.site_claim_eligible)
        self.assertEqual(origin.site_claim_status, "site_claim_rule_unverified")

    def test_authoritative_catalog_emits_all_and_only_rully_premier_cru_claims(self):
        white = [item for item in self.items if item.legal_spec_id == "fr:rully:white-premier-cru"]
        red = [item for item in self.items if item.legal_spec_id == "fr:rully:red-premier-cru"]
        white_site_rows = [item for item in white if item.wine.vineyard]
        red_site_rows = [item for item in red if item.wine.vineyard]

        self.assertEqual(len(white), 48)
        self.assertEqual(len(white_site_rows), 46)
        self.assertEqual(len(red), 24)
        self.assertEqual(len(red_site_rows), 23)
        self.assertEqual(len({item.wine.vineyard for item in white_site_rows}), 23)
        self.assertEqual(len({item.wine.vineyard for item in red_site_rows}), 23)


class CortonHandoffRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = WineOriginFactory().catalog

    def test_corton_has_exactly_the_24_legal_red_suffix_climats(self):
        actual = {
            site.name for site in self.catalog.named_sites
            if site.parent == "Corton"
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        }
        self.assertEqual(actual, EXPECTED_CORTON_SUFFIXES)

    def test_handoff_false_positive_corton_suffixes_are_not_promoted(self):
        actual = {
            site.name for site in self.catalog.named_sites
            if site.parent == "Corton" and site.site_type == "climat"
        }
        self.assertTrue(HANDOFF_FALSE_POSITIVE_CORTON_SUFFIXES.isdisjoint(actual))
        self.assertIn("Clos des Meix", actual)
        self.assertIn("Les Chaumes", actual)


if __name__ == "__main__":
    unittest.main()
