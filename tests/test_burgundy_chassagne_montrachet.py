from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.site_claims import SiteClaimRegistry


EXPECTED = {
    "white standard": {
        "id": "fr:chassagne-montrachet:white-standard",
        "must": 178.0,
        "potential": 11.0,
        "yield": 57.0,
        "total_alcohol": 13.5,
        "sugar": 3.0,
        "malic": None,
    },
    "red standard": {
        "id": "fr:chassagne-montrachet:red-standard",
        "must": 180.0,
        "potential": 10.5,
        "yield": 50.0,
        "total_alcohol": 13.5,
        "sugar": 2.0,
        "malic": 0.4,
    },
    "white premier cru": {
        "id": "fr:chassagne-montrachet:white-premier-cru",
        "must": 187.0,
        "potential": 11.5,
        "yield": 55.0,
        "total_alcohol": 14.0,
        "sugar": 3.0,
        "malic": None,
    },
    "red premier cru": {
        "id": "fr:chassagne-montrachet:red-premier-cru",
        "must": 189.0,
        "potential": 11.0,
        "yield": 48.0,
        "total_alcohol": 14.0,
        "sugar": 2.0,
        "malic": 0.4,
    },
}


class ChassagneMontrachetLegalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_four_color_and_level_paths_resolve_with_exact_machine_limits(self):
        for variant, expected in EXPECTED.items():
            spec = self.registry.resolve(
                country="France",
                appellation="Chassagne-Montrachet",
                variant=variant,
            )
            self.assertIsNotNone(spec, variant)
            self.assertEqual(spec.id, expected["id"])
            self.assertEqual(spec.min_must_sugar_g_l, expected["must"])
            self.assertEqual(spec.min_potential_alcohol_pct, expected["potential"])
            self.assertEqual(spec.max_yield_hl_ha, expected["yield"])
            self.assertEqual(spec.max_total_alcohol_pct, expected["total_alcohol"])
            self.assertEqual(spec.max_residual_sugar_g_l, expected["sugar"])
            self.assertEqual(spec.max_malic_acid_g_l, expected["malic"])
            self.assertEqual(
                (
                    spec.min_elevage_year_offset,
                    spec.min_elevage_until_month,
                    spec.min_elevage_until_day,
                ),
                (1, 6, 15),
            )
            self.assertEqual(
                (
                    spec.release_year_offset,
                    spec.earliest_release_month,
                    spec.earliest_release_day,
                ),
                (1, 6, 30),
            )

    def test_white_paths_allow_chardonnay_and_pinot_blanc(self):
        for variant in ("white standard", "white premier cru"):
            spec = self.registry.resolve(
                country="France",
                appellation="Chassagne-Montrachet",
                variant=variant,
            )
            self.assertIsNotNone(spec)
            self.assertTrue(
                self.registry.evaluate_blend(spec, {"Chardonnay": 100.0}).eligible
            )
            self.assertTrue(
                self.registry.evaluate_blend(spec, {"Pinot Blanc": 100.0}).eligible
            )
            self.assertFalse(
                self.registry.evaluate_blend(spec, {"Pinot Noir": 100.0}).eligible
            )

    def test_red_paths_are_conservative_pinot_noir_only(self):
        for variant in ("red standard", "red premier cru"):
            spec = self.registry.resolve(
                country="France",
                appellation="Chassagne-Montrachet",
                variant=variant,
            )
            self.assertIsNotNone(spec)
            self.assertTrue(
                self.registry.evaluate_blend(spec, {"Pinot Noir": 100.0}).eligible
            )
            self.assertFalse(
                self.registry.evaluate_blend(spec, {"Chardonnay": 100.0}).eligible
            )

    def test_premier_cru_production_limits_fail_closed(self):
        white = self.registry.resolve(
            country="France",
            appellation="Chassagne-Montrachet",
            variant="white premier cru",
        )
        red = self.registry.resolve(
            country="France",
            appellation="Chassagne-Montrachet",
            variant="red premier cru",
        )
        self.assertIsNotNone(white)
        self.assertIsNotNone(red)

        self.assertFalse(
            self.registry.validate_production(
                white,
                wine_yield_hl_ha=55.0,
                must_sugar_g_l=186.9,
                potential_alcohol_pct=11.5,
                require_complete=True,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                red,
                wine_yield_hl_ha=48.1,
                must_sugar_g_l=189.0,
                potential_alcohol_pct=11.0,
                require_complete=True,
            ).eligible
        )

    def test_red_premier_cru_analytical_and_calendar_rules_fail_closed(self):
        spec = self.registry.resolve(
            country="France",
            appellation="Chassagne-Montrachet",
            variant="red premier cru",
        )
        self.assertIsNotNone(spec)

        common = dict(
            total_aging_months=0,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.2,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        exact = self.registry.validate_release(
            spec,
            total_alcohol_pct=13.5,
            **common,
        )
        too_high_alcohol = self.registry.validate_release(
            spec,
            total_alcohol_pct=14.01,
            **common,
        )
        too_much_malic = self.registry.validate_release(
            spec,
            total_alcohol_pct=13.5,
            **{**common, "malic_acid_g_l": 0.41},
        )
        early_release = self.registry.validate_release(
            spec,
            total_alcohol_pct=13.5,
            **{**common, "release_day": 29},
        )
        early_elevage = self.registry.validate_release(
            spec,
            total_alcohol_pct=13.5,
            **{**common, "elevage_end_day": 14},
        )
        self.assertTrue(exact.eligible)
        self.assertFalse(too_high_alcohol.eligible)
        self.assertFalse(too_much_malic.eligible)
        self.assertFalse(early_release.eligible)
        self.assertFalse(early_elevage.eligible)


class ChassagneMontrachetSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = WorldWineKnowledgeCatalog()
        cls.sites = [
            site
            for site in cls.catalog.named_sites
            if site.parent == "Chassagne-Montrachet"
        ]

    def test_full_current_site_inventory_is_loaded(self):
        climats = [site for site in self.sites if site.site_type == "climat"]
        lieux_dits = [site for site in self.sites if site.site_type == "lieu_dit"]
        self.assertEqual(len(climats), 55)
        self.assertEqual(len(lieux_dits), 46)
        self.assertEqual(
            {site.legal_status for site in climats},
            {"official_appellation_climat"},
        )
        self.assertEqual(
            {site.legal_status for site in lieux_dits},
            {"official_appellation_lieu_dit"},
        )

    def test_same_name_climat_and_lieu_dit_are_distinct_identities(self):
        chaumes = [site for site in self.sites if site.name == "Les Chaumes"]
        self.assertEqual(len(chaumes), 2)
        self.assertEqual({site.site_type for site in chaumes}, {"climat", "lieu_dit"})
        self.assertEqual(len({site.id for site in chaumes}), 2)

    def test_claim_rule_is_auto_discovered(self):
        rules = SiteClaimRegistry().rules
        ids = {rule.id for rule in rules}
        self.assertIn(
            "siteclaim:fr:chassagne-montrachet:premier-cru-climat",
            ids,
        )


class ChassagneMontrachetAuthoritativeCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = AuthoritativeCatalogGenerator().generate(
            as_of_year=2026,
            include_site_claims=True,
        )
        cls.rows = [
            item
            for item in cls.items
            if item.wine.appellation == "Chassagne-Montrachet"
        ]

    def test_exact_record_counts_by_strict_spec(self):
        counts = {
            spec_id: len([item for item in self.rows if item.legal_spec_id == spec_id])
            for spec_id in {expected["id"] for expected in EXPECTED.values()}
        }
        self.assertEqual(counts["fr:chassagne-montrachet:white-standard"], 2)
        self.assertEqual(counts["fr:chassagne-montrachet:red-standard"], 1)
        self.assertEqual(counts["fr:chassagne-montrachet:white-premier-cru"], 112)
        self.assertEqual(counts["fr:chassagne-montrachet:red-premier-cru"], 56)
        self.assertEqual(len(self.rows), 171)

    def test_all_55_premier_cru_climats_enter_each_color_path(self):
        white_sites = {
            item.wine.vineyard
            for item in self.rows
            if item.legal_spec_id == "fr:chassagne-montrachet:white-premier-cru"
            and item.wine.vineyard
        }
        red_sites = {
            item.wine.vineyard
            for item in self.rows
            if item.legal_spec_id == "fr:chassagne-montrachet:red-premier-cru"
            and item.wine.vineyard
        }
        self.assertEqual(len(white_sites), 55)
        self.assertEqual(len(red_sites), 55)
        self.assertEqual(white_sites, red_sites)
        self.assertIn("Morgeot", white_sites)
        self.assertIn("La Romanée", red_sites)

    def test_ordinary_lieux_dits_do_not_leak_into_legal_claims(self):
        vineyard_names = {item.wine.vineyard for item in self.rows if item.wine.vineyard}
        self.assertNotIn("Puits Merdreaux", vineyard_names)
        self.assertNotIn("Les Houillères", vineyard_names)
        self.assertNotIn("Blanchot Dessous", vineyard_names)

    def test_standard_wines_have_no_premier_cru_site_suffix(self):
        standard = [
            item
            for item in self.rows
            if item.legal_spec_id in {
                "fr:chassagne-montrachet:white-standard",
                "fr:chassagne-montrachet:red-standard",
            }
        ]
        self.assertEqual(len(standard), 3)
        self.assertTrue(all(item.wine.vineyard == "" for item in standard))


if __name__ == "__main__":
    unittest.main()
