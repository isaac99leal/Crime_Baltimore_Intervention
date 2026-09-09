from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory
from sommelier_v2.knowledge.regional_rules import OriginConstraintError


LOCHE_CLIMATS = {"Les Mûres"}
VINZELLES_CLIMATS = {"Les Longeays", "Les Pétaux", "Les Quarts"}


class MaconnaisPremierCruStrictSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_both_premier_cru_specs_resolve_with_exact_limits(self):
        for appellation, spec_id in (
            ("Pouilly-Loché", "fr:pouilly-loche:premier-cru"),
            ("Pouilly-Vinzelles", "fr:pouilly-vinzelles:premier-cru"),
        ):
            spec = self.registry.resolve(country="France", appellation=appellation, variant="premier cru")
            self.assertIsNotNone(spec, appellation)
            self.assertEqual(spec.id, spec_id)
            self.assertEqual(spec.wine_style, "white")
            self.assertEqual(spec.allowed_grapes, ("Chardonnay",))
            self.assertEqual(spec.min_must_sugar_g_l, 195.0)
            self.assertEqual(spec.min_potential_alcohol_pct, 12.0)
            self.assertEqual(spec.max_total_alcohol_pct, 13.5)
            self.assertEqual(spec.max_yield_hl_ha, 58.0)
            self.assertEqual(spec.max_residual_sugar_g_l, 3.0)
            self.assertEqual(
                (spec.min_elevage_year_offset, spec.min_elevage_until_month, spec.min_elevage_until_day),
                (1, 7, 1),
            )
            self.assertEqual(
                (spec.release_year_offset, spec.earliest_release_month, spec.earliest_release_day),
                (1, 7, 15),
            )

    def test_positive_path_is_chardonnay_only(self):
        for appellation in ("Pouilly-Loché", "Pouilly-Vinzelles"):
            spec = self.registry.resolve(country="France", appellation=appellation, variant="premier cru")
            self.assertIsNotNone(spec)
            self.assertTrue(self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible)
            self.assertFalse(self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible)
            self.assertFalse(self.registry.evaluate_blend(spec, {"Chardonnay": 99, "Pinot Blanc": 1}).eligible)

    def test_release_and_analytical_boundaries_fail_closed(self):
        for appellation in ("Pouilly-Loché", "Pouilly-Vinzelles"):
            spec = self.registry.resolve(country="France", appellation=appellation, variant="premier cru")
            self.assertIsNotNone(spec)
            valid = self.registry.validate_release(
                spec,
                total_aging_months=0,
                total_alcohol_pct=13.5,
                residual_sugar_g_l=3.0,
                vintage_year=2025,
                elevage_end_year=2026,
                elevage_end_month=7,
                elevage_end_day=1,
                release_year=2026,
                release_month=7,
                release_day=15,
                require_complete=True,
            )
            early = self.registry.validate_release(
                spec,
                total_aging_months=0,
                total_alcohol_pct=13.5,
                residual_sugar_g_l=3.0,
                vintage_year=2025,
                elevage_end_year=2026,
                elevage_end_month=7,
                elevage_end_day=1,
                release_year=2026,
                release_month=7,
                release_day=14,
                require_complete=True,
            )
            sugar_fail = self.registry.validate_release(
                spec,
                total_aging_months=0,
                total_alcohol_pct=13.5,
                residual_sugar_g_l=3.01,
                vintage_year=2025,
                elevage_end_year=2026,
                elevage_end_month=7,
                elevage_end_day=1,
                release_year=2026,
                release_month=7,
                release_day=15,
                require_complete=True,
            )
            alcohol_fail = self.registry.validate_release(
                spec,
                total_aging_months=0,
                total_alcohol_pct=13.51,
                residual_sugar_g_l=3.0,
                vintage_year=2025,
                elevage_end_year=2026,
                elevage_end_month=7,
                elevage_end_day=1,
                release_year=2026,
                release_month=7,
                release_day=15,
                require_complete=True,
            )
            self.assertTrue(valid.eligible)
            self.assertFalse(early.eligible)
            self.assertFalse(sugar_fail.eligible)
            self.assertFalse(alcohol_fail.eligible)

    def test_manual_harvest_transition_is_not_generalized(self):
        for appellation in ("Pouilly-Loché", "Pouilly-Vinzelles"):
            spec = self.registry.resolve(country="France", appellation=appellation, variant="premier cru")
            self.assertIsNotNone(spec)
            self.assertFalse(spec.manual_harvest_required)


class MaconnaisPremierCruSiteClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()
        cls.catalog = cls.factory.catalog

    def sites(self, parent: str):
        return [
            site for site in self.catalog.named_sites
            if site.parent == parent
            and site.site_type == "climat"
            and site.legal_status == "official_appellation_climat"
        ]

    def test_parent_scoped_climat_sets_are_exact(self):
        self.assertEqual({site.name for site in self.sites("Pouilly-Loché")}, LOCHE_CLIMATS)
        self.assertEqual({site.name for site in self.sites("Pouilly-Vinzelles")}, VINZELLES_CLIMATS)

    def test_every_parent_scoped_premier_cru_claim_passes(self):
        for parent, names in (("Pouilly-Loché", LOCHE_CLIMATS), ("Pouilly-Vinzelles", VINZELLES_CLIMATS)):
            for site in self.sites(parent):
                self.assertIn(site.name, names)
                origin = self.factory.create(OriginRequest(
                    country="France",
                    region="Bourgogne",
                    appellation=parent,
                    grapes={"Chardonnay": 100},
                    vintage_year=2025,
                    label_scope="regulated_gi",
                    site_id=site.id,
                    wine_variant="premier cru",
                ))
                self.assertTrue(origin.site_claim_eligible, (parent, site.name))

    def test_cross_parent_site_identity_cannot_substitute(self):
        vinzelles = next(site for site in self.sites("Pouilly-Vinzelles") if site.name == "Les Quarts")
        with self.assertRaises(OriginConstraintError):
            self.factory.create(OriginRequest(
                country="France",
                region="Bourgogne",
                appellation="Pouilly-Loché",
                grapes={"Chardonnay": 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=vinzelles.id,
                wine_variant="premier cru",
            ))


class MaconnaisPremierCruAuthoritativeCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = AuthoritativeCatalogGenerator().generate(as_of_year=2026, include_site_claims=True)

    def test_pouilly_loche_has_base_plus_les_mures(self):
        rows = [item for item in self.items if item.legal_spec_id == "fr:pouilly-loche:premier-cru"]
        self.assertEqual(len(rows), 2)
        self.assertEqual({item.wine.vineyard for item in rows if item.wine.vineyard}, LOCHE_CLIMATS)

    def test_pouilly_vinzelles_has_base_plus_three_climats(self):
        rows = [item for item in self.items if item.legal_spec_id == "fr:pouilly-vinzelles:premier-cru"]
        self.assertEqual(len(rows), 4)
        self.assertEqual({item.wine.vineyard for item in rows if item.wine.vineyard}, VINZELLES_CLIMATS)


if __name__ == "__main__":
    unittest.main()
