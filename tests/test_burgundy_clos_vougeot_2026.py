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
from sommelier_v2.knowledge.origin_factory import OriginRequest
from sommelier_v2.domain import WineStyle


class ClosVougeot2026LegalSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()
        cls.spec = cls.registry.resolve(
            country="France",
            appellation="Clos de Vougeot",
            variant="grand cru",
        )

    def test_current_2026_spec_is_loaded(self):
        self.assertIsNotNone(self.spec)
        self.assertEqual(self.spec.id, "fr:clos-de-vougeot:grand-cru")
        self.assertEqual(self.spec.effective_from, "2026-03-29")
        self.assertEqual(self.spec.allowed_grapes, ("Pinot Noir",))
        self.assertEqual(self.spec.min_must_sugar_g_l, 198.0)
        self.assertEqual(self.spec.min_potential_alcohol_pct, 11.5)
        self.assertEqual(self.spec.max_total_alcohol_pct, 14.5)
        self.assertEqual(self.spec.max_yield_hl_ha, 42.0)
        self.assertEqual(self.spec.max_residual_sugar_g_l, 2.0)
        self.assertEqual(self.spec.max_malic_acid_g_l, 0.4)
        self.assertEqual(self.spec.min_elevage_year_offset, 1)
        self.assertEqual(
            (self.spec.min_elevage_until_month, self.spec.min_elevage_until_day),
            (6, 15),
        )
        self.assertEqual(self.spec.release_year_offset, 1)
        self.assertEqual(
            (self.spec.earliest_release_month, self.spec.earliest_release_day),
            (6, 30),
        )

    def test_clos_vougeot_alias_resolves_to_same_aoc(self):
        alias = self.registry.resolve(
            country="France",
            appellation="Clos Vougeot",
            variant="grand cru",
        )
        self.assertIsNotNone(alias)
        self.assertEqual(alias.id, self.spec.id)

    def test_must_sugar_is_required_and_enforced(self):
        missing = self.registry.validate_production(
            self.spec,
            wine_yield_hl_ha=40.0,
            potential_alcohol_pct=12.0,
            require_complete=True,
        )
        low = self.registry.validate_production(
            self.spec,
            wine_yield_hl_ha=40.0,
            must_sugar_g_l=197.9,
            potential_alcohol_pct=12.0,
            require_complete=True,
        )
        exact = self.registry.validate_production(
            self.spec,
            wine_yield_hl_ha=42.0,
            must_sugar_g_l=198.0,
            potential_alcohol_pct=11.5,
            require_complete=True,
        )
        self.assertFalse(missing.eligible)
        self.assertFalse(low.eligible)
        self.assertTrue(exact.eligible)

    def test_total_alcohol_ceiling_is_distinct_from_actual_alcohol(self):
        good = self.registry.validate_release(
            self.spec,
            total_aging_months=0,
            total_alcohol_pct=14.5,
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
        high = self.registry.validate_release(
            self.spec,
            total_aging_months=0,
            total_alcohol_pct=14.51,
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
        self.assertTrue(good.eligible)
        self.assertFalse(high.eligible)

    def test_calendar_rules_are_day_exact(self):
        before_elevage = self.registry.validate_release(
            self.spec,
            total_aging_months=0,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.2,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=14,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        before_release = self.registry.validate_release(
            self.spec,
            total_aging_months=0,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.2,
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
            self.spec,
            total_aging_months=0,
            total_alcohol_pct=14.0,
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
        self.assertFalse(before_elevage.eligible)
        self.assertFalse(before_release.eligible)
        self.assertTrue(exact.eligible)


class ClosVougeotBuilderTests(unittest.TestCase):
    @staticmethod
    def request(**changes) -> WineBuildRequest:
        values = dict(
            id="strict:test:clos-vougeot",
            producer="Simulation Producer",
            label="Clos de Vougeot",
            origin=OriginRequest(
                country="France",
                region="Clos de Vougeot",
                appellation="Clos de Vougeot",
                grapes={"Pinot Noir": 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                wine_variant="grand cru",
            ),
            style=WineStyle.RED,
            classification="grand cru",
            alcohol=13.5,
            wine_yield_hl_ha=40.0,
            must_sugar_g_l=205.0,
            potential_alcohol_pct=12.0,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.2,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
        )
        values.update(changes)
        return WineBuildRequest(**values)

    def test_builder_accepts_complete_current_rule_evidence(self):
        result = ConstrainedWineBuilder().build(self.request())
        self.assertEqual(result.evidence.legal_spec_id, "fr:clos-de-vougeot:grand-cru")
        self.assertEqual(result.evidence.production_status, "production_eligible_sourced_spec")
        self.assertEqual(result.evidence.release_status, "release_eligible_sourced_spec")

    def test_builder_fails_closed_without_maturity_evidence(self):
        with self.assertRaises(WineProductionConstraintError):
            ConstrainedWineBuilder().build(self.request(must_sugar_g_l=None))

    def test_builder_rejects_early_calendar_release(self):
        with self.assertRaises(WineReleaseConstraintError):
            ConstrainedWineBuilder().build(self.request(release_day=29))


class ClosVougeotAuthoritativeCatalogTests(unittest.TestCase):
    def test_default_catalog_generates_current_clos_vougeot_record(self):
        items = AuthoritativeCatalogGenerator().generate(
            as_of_year=2026,
            include_site_claims=True,
        )
        rows = [
            item for item in items
            if item.legal_spec_id == "fr:clos-de-vougeot:grand-cru"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].wine.appellation, "Clos de Vougeot")
        self.assertEqual(rows[0].wine.classification, "grand cru")
        self.assertEqual(rows[0].wine.grapes, ("Pinot Noir",))
        self.assertEqual(rows[0].wine.vineyard, "")
        self.assertIn("release no earlier than 06-30", rows[0].wine.winemaking_notes)


if __name__ == "__main__":
    unittest.main()
