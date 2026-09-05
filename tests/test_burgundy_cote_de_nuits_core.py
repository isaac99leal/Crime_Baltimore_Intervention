from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory


class CoteDeNuitsStrictSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_gevrey_standard_and_premier_cru(self):
        standard = self.registry.resolve(country="France", appellation="Gevrey-Chambertin", variant="standard")
        premier = self.registry.resolve(country="France", appellation="Gevrey-Chambertin", variant="premier cru")
        self.assertIsNotNone(standard)
        self.assertIsNotNone(premier)
        self.assertEqual((standard.min_potential_alcohol_pct, standard.max_yield_hl_ha), (10.5, 50.0))
        self.assertEqual((premier.min_potential_alcohol_pct, premier.max_yield_hl_ha), (11.0, 48.0))
        self.assertEqual((standard.max_residual_sugar_g_l, standard.max_malic_acid_g_l), (2.0, 0.4))
        self.assertTrue(self.registry.evaluate_blend(standard, "Pinot Noir").eligible)
        self.assertFalse(self.registry.evaluate_blend(standard, "Chardonnay").eligible)

    def test_morey_color_and_level_matrix(self):
        expected = {
            "white standard": (11.0, 57.0, 3.0, None),
            "red standard": (10.5, 50.0, 2.0, 0.4),
            "white premier cru": (11.5, 55.0, 3.0, None),
            "red premier cru": (11.0, 48.0, 2.0, 0.4),
        }
        for variant, values in expected.items():
            spec = self.registry.resolve(country="France", appellation="Morey-Saint-Denis", variant=variant)
            self.assertIsNotNone(spec, variant)
            self.assertEqual(
                (spec.min_potential_alcohol_pct, spec.max_yield_hl_ha, spec.max_residual_sugar_g_l, spec.max_malic_acid_g_l),
                values,
            )
            self.assertEqual(spec.release_year_offset, 1)

    def test_vosne_standard_and_premier_cru(self):
        standard = self.registry.resolve(country="France", appellation="Vosne-Romanée", variant="standard")
        premier = self.registry.resolve(country="France", appellation="Vosne-Romanée", variant="premier cru")
        self.assertIsNotNone(standard)
        self.assertIsNotNone(premier)
        self.assertEqual((standard.min_potential_alcohol_pct, standard.max_yield_hl_ha), (10.5, 50.0))
        self.assertEqual((premier.min_potential_alcohol_pct, premier.max_yield_hl_ha), (11.0, 48.0))
        self.assertEqual((premier.max_residual_sugar_g_l, premier.max_malic_acid_g_l), (2.0, 0.4))

    def test_nuits_color_and_level_matrix(self):
        expected = {
            "white standard": (11.0, 57.0, 3.0, None),
            "red standard": (10.5, 50.0, 2.0, 0.4),
            "white premier cru": (11.5, 55.0, 3.0, None),
            "red premier cru": (11.0, 48.0, 2.0, 0.4),
        }
        for variant, values in expected.items():
            spec = self.registry.resolve(country="France", appellation="Nuits-Saint-Georges", variant=variant)
            self.assertIsNotNone(spec, variant)
            self.assertEqual(
                (spec.min_potential_alcohol_pct, spec.max_yield_hl_ha, spec.max_residual_sugar_g_l, spec.max_malic_acid_g_l),
                values,
            )
            self.assertEqual(spec.release_year_offset, 1)


class CoteDeNuitsSiteClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()

    @classmethod
    def site(cls, parent: str, name: str, site_type: str = "climat"):
        return next(
            site for site in cls.factory.catalog.named_sites
            if site.parent == parent and site.name == name and site.site_type == site_type
        )

    def origin(self, parent: str, name: str, variant: str, grapes: dict[str, int]):
        site = self.site(parent, name)
        return self.factory.create(
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

    def test_gevrey_clos_saint_jacques_passes(self):
        origin = self.origin("Gevrey-Chambertin", "Clos Saint-Jacques", "premier cru", {"Pinot Noir": 100})
        self.assertTrue(origin.site_claim_eligible)
        self.assertEqual(origin.site_claim_rule_id, "siteclaim:fr:gevrey-chambertin:premier-cru-climat")

    def test_morey_monts_luisants_passes_for_both_general_color_paths(self):
        for variant, grapes in (
            ("white premier cru", {"Chardonnay": 100}),
            ("red premier cru", {"Pinot Noir": 100}),
        ):
            origin = self.origin("Morey-Saint-Denis", "Monts Luisants", variant, grapes)
            self.assertTrue(origin.site_claim_eligible, variant)

    def test_vosne_cros_parantoux_passes(self):
        origin = self.origin("Vosne-Romanée", "Cros Parantoux", "premier cru", {"Pinot Noir": 100})
        self.assertTrue(origin.site_claim_eligible)
        self.assertEqual(origin.site_claim_rule_id, "siteclaim:fr:vosne-romanee:premier-cru-climat")

    def test_nuits_les_saints_georges_passes_for_both_colors(self):
        for variant, grapes in (
            ("white premier cru", {"Chardonnay": 100}),
            ("red premier cru", {"Pinot Noir": 100}),
        ):
            origin = self.origin("Nuits-Saint-Georges", "Les Saints-Georges", variant, grapes)
            self.assertTrue(origin.site_claim_eligible, variant)

    def test_ordinary_lieux_dits_remain_fail_closed(self):
        cases = (
            ("Gevrey-Chambertin", "Roncevie", "standard", {"Pinot Noir": 100}),
            ("Morey-Saint-Denis", "Très Girard", "red standard", {"Pinot Noir": 100}),
            ("Vosne-Romanée", "Les Damaudes", "standard", {"Pinot Noir": 100}),
            ("Nuits-Saint-Georges", "Les Maladières", "red standard", {"Pinot Noir": 100}),
        )
        for parent, name, variant, grapes in cases:
            site = self.site(parent, name, "lieu_dit")
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


class CoteDeNuitsCatalogTests(unittest.TestCase):
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

    def test_exact_premier_cru_counts(self):
        self.assertEqual(len(self.sites("fr:gevrey-chambertin:premier-cru")), 26)
        self.assertEqual(len(self.sites("fr:morey-saint-denis:white-premier-cru")), 20)
        self.assertEqual(len(self.sites("fr:morey-saint-denis:red-premier-cru")), 20)
        self.assertEqual(len(self.sites("fr:vosne-romanee:premier-cru")), 14)
        self.assertEqual(len(self.sites("fr:nuits-saint-georges:white-premier-cru")), 41)
        self.assertEqual(len(self.sites("fr:nuits-saint-georges:red-premier-cru")), 41)

    def test_named_site_identity_counts(self):
        expected = {
            "Gevrey-Chambertin": (26, 65),
            "Morey-Saint-Denis": (20, 23),
            "Vosne-Romanée": (14, 26),
            "Nuits-Saint-Georges": (41, 34),
        }
        for parent, (climats, lieux_dits) in expected.items():
            rows = [site for site in self.generator.catalog.named_sites if site.parent == parent]
            self.assertEqual(sum(site.site_type == "climat" for site in rows), climats, parent)
            self.assertEqual(sum(site.site_type == "lieu_dit" for site in rows), lieux_dits, parent)

    def test_same_name_climat_and_lieu_dit_identities_are_preserved(self):
        cases = (
            ("Gevrey-Chambertin", "La Bossière"),
            ("Morey-Saint-Denis", "Clos des Ormes"),
            ("Morey-Saint-Denis", "Le Village"),
            ("Morey-Saint-Denis", "Monts Luisants"),
            ("Nuits-Saint-Georges", "En la Perrière Noblot"),
            ("Nuits-Saint-Georges", "Les Damodes"),
            ("Nuits-Saint-Georges", "Les Hauts Pruliers"),
            ("Nuits-Saint-Georges", "Les Vallerots"),
        )
        for parent, name in cases:
            rows = [
                site for site in self.generator.catalog.named_sites
                if site.parent == parent and site.name == name
            ]
            self.assertEqual({site.site_type for site in rows}, {"climat", "lieu_dit"}, (parent, name))
            self.assertEqual(len({site.id for site in rows}), 2, (parent, name))


if __name__ == "__main__":
    unittest.main()
