from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


BURGUNDY_MATRIX = {
    "white standard": (178.0, 11.0, 57.0, 13.5),
    "red standard": (180.0, 10.5, 50.0, 13.5),
    "white premier cru": (187.0, 11.5, 55.0, 14.0),
    "red premier cru": (189.0, 11.0, 48.0, 14.0),
}

PERNAND_WHITE_ONLY = {"Sous Frétille", "Clos Berthet", "Village de Pernand"}
PERNAND_RED_ALLOWED = {
    "Creux de la Net",
    "En Caradeux",
    "Ile des Vergelesses",
    "Les Fichots",
    "Vergelesses",
}
AUXEY_SITES = {
    "Bas des Duresses",
    "Climat du Val",
    "Clos du Val",
    "La Chapelle",
    "Les Bréterins",
    "Les Duresses",
    "Les Ecussaux",
    "Les Grands Champs",
    "Reugne",
}


class PernandAuxeyLegalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_both_appellations_expose_four_strict_color_level_paths(self):
        for appellation, slug in (
            ("Pernand-Vergelesses", "pernand-vergelesses"),
            ("Auxey-Duresses", "auxey-duresses"),
        ):
            for variant, (sugar, alcohol, yield_hl, max_total) in BURGUNDY_MATRIX.items():
                spec = self.registry.resolve(
                    country="France", appellation=appellation, variant=variant
                )
                self.assertIsNotNone(spec, (appellation, variant))
                self.assertEqual(spec.id, f"fr:{slug}:{variant.replace(' ', '-')}")
                self.assertEqual(spec.min_must_sugar_g_l, sugar)
                self.assertEqual(spec.min_potential_alcohol_pct, alcohol)
                self.assertEqual(spec.max_yield_hl_ha, yield_hl)
                self.assertEqual(spec.max_total_alcohol_pct, max_total)

    def test_pernand_white_pinot_gris_is_accessory_but_chardonnay_and_pinot_blanc_are_principal(self):
        spec = self.registry.resolve(
            country="France",
            appellation="Pernand-Vergelesses",
            variant="white premier cru",
        )
        self.assertIsNotNone(spec)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Pinot Blanc": 100}).eligible)
        self.assertFalse(self.registry.evaluate_blend(spec, {"Pinot Gris": 100}).eligible)
        self.assertTrue(
            self.registry.evaluate_blend(
                spec, {"Chardonnay": 50, "Pinot Blanc": 20, "Pinot Gris": 30}
            ).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(
                spec, {"Chardonnay": 49, "Pinot Blanc": 20, "Pinot Gris": 31}
            ).eligible
        )

    def test_auxey_white_allows_chardonnay_and_pinot_blanc_paths(self):
        spec = self.registry.resolve(
            country="France", appellation="Auxey-Duresses", variant="white premier cru"
        )
        self.assertIsNotNone(spec)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Pinot Blanc": 100}).eligible)

    def test_red_paths_remain_conservative_pinot_noir_only(self):
        for appellation in ("Pernand-Vergelesses", "Auxey-Duresses"):
            spec = self.registry.resolve(
                country="France", appellation=appellation, variant="red premier cru"
            )
            self.assertIsNotNone(spec)
            self.assertTrue(self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible)
            self.assertFalse(self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible)

    def test_pernand_village_and_premier_cru_have_different_release_calendars(self):
        village = self.registry.resolve(
            country="France", appellation="Pernand-Vergelesses", variant="white standard"
        )
        premier = self.registry.resolve(
            country="France", appellation="Pernand-Vergelesses", variant="white premier cru"
        )
        self.assertIsNotNone(village)
        self.assertIsNotNone(premier)
        self.assertEqual(
            (village.min_elevage_until_month, village.min_elevage_until_day,
             village.earliest_release_month, village.earliest_release_day),
            (3, 15, 3, 31),
        )
        self.assertEqual(
            (premier.min_elevage_until_month, premier.min_elevage_until_day,
             premier.earliest_release_month, premier.earliest_release_day),
            (6, 15, 6, 30),
        )

        village_exact = self.registry.validate_release(
            village,
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
        premier_too_early = self.registry.validate_release(
            premier,
            total_aging_months=0,
            total_alcohol_pct=13.5,
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
        self.assertTrue(village_exact.eligible)
        self.assertFalse(premier_too_early.eligible)

    def test_auxey_uses_june_calendar_at_both_levels(self):
        for variant in ("white standard", "red standard", "white premier cru", "red premier cru"):
            spec = self.registry.resolve(
                country="France", appellation="Auxey-Duresses", variant=variant
            )
            self.assertIsNotNone(spec)
            self.assertEqual(
                (spec.min_elevage_until_month, spec.min_elevage_until_day,
                 spec.earliest_release_month, spec.earliest_release_day),
                (6, 15, 6, 30),
            )


class PernandAuxeySiteAndCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = WorldWineKnowledgeCatalog()
        cls.items = AuthoritativeCatalogGenerator(catalog=cls.knowledge).generate(
            as_of_year=2026, include_site_claims=True
        )

    def _site_names(self, parent: str) -> set[str]:
        return {
            site.name
            for site in self.knowledge.named_sites
            if site.parent == parent
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        }

    def test_exact_premier_cru_site_inventories(self):
        pernand = self._site_names("Pernand-Vergelesses")
        auxey = self._site_names("Auxey-Duresses")
        self.assertEqual(len(pernand), 8)
        self.assertEqual(pernand, PERNAND_WHITE_ONLY | PERNAND_RED_ALLOWED)
        self.assertEqual(len(auxey), 9)
        self.assertEqual(auxey, AUXEY_SITES)

    def test_pernand_catalog_enforces_color_specific_site_matrix(self):
        white = [
            item for item in self.items
            if item.legal_spec_id == "fr:pernand-vergelesses:white-premier-cru"
        ]
        red = [
            item for item in self.items
            if item.legal_spec_id == "fr:pernand-vergelesses:red-premier-cru"
        ]
        # Chardonnay and Pinot Blanc are independently legal white paths.
        self.assertEqual(len(white), 18)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in white), 16)
        self.assertEqual({item.wine.vineyard for item in white if item.wine.vineyard},
                         PERNAND_WHITE_ONLY | PERNAND_RED_ALLOWED)

        self.assertEqual(len(red), 6)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in red), 5)
        self.assertEqual({item.wine.vineyard for item in red if item.wine.vineyard},
                         PERNAND_RED_ALLOWED)
        for white_only in PERNAND_WHITE_ONLY:
            self.assertNotIn(white_only, {item.wine.vineyard for item in red})

    def test_auxey_catalog_generates_all_nine_sites_for_both_colors(self):
        white = [
            item for item in self.items
            if item.legal_spec_id == "fr:auxey-duresses:white-premier-cru"
        ]
        red = [
            item for item in self.items
            if item.legal_spec_id == "fr:auxey-duresses:red-premier-cru"
        ]
        self.assertEqual(len(white), 20)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in white), 18)
        self.assertEqual({item.wine.vineyard for item in white if item.wine.vineyard}, AUXEY_SITES)
        self.assertEqual(len(red), 10)
        self.assertEqual(sum(bool(item.wine.vineyard) for item in red), 9)
        self.assertEqual({item.wine.vineyard for item in red if item.wine.vineyard}, AUXEY_SITES)

    def test_standard_wines_do_not_inherit_premier_cru_site_claims(self):
        standard_ids = {
            "fr:pernand-vergelesses:white-standard",
            "fr:pernand-vergelesses:red-standard",
            "fr:auxey-duresses:white-standard",
            "fr:auxey-duresses:red-standard",
        }
        rows = [item for item in self.items if item.legal_spec_id in standard_ids]
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(item.wine.vineyard == "" for item in rows))


if __name__ == "__main__":
    unittest.main()
