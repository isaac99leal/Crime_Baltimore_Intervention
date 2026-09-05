from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import (
    AuthoritativeCatalogGenerator,
    LEGAL_SNAPSHOT_AS_OF_YEAR,
)
from sommelier_v2.catalog import load_catalog
from sommelier_v2.generation import WineReleaseConstraintError


class AuthoritativeCatalogGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = AuthoritativeCatalogGenerator()

    def test_small_generation_passes_full_legal_pipeline(self):
        items = self.generator.generate(
            as_of_year=LEGAL_SNAPSHOT_AS_OF_YEAR,
            include_site_claims=True,
            max_sites_per_spec=2,
        )
        self.assertGreater(len(items), 20)
        for item in items:
            self.assertEqual(
                item.generated.evidence.origin_status,
                "appellation_eligible_sourced_spec",
            )
            self.assertEqual(
                item.generated.evidence.production_status,
                "production_eligible_sourced_spec",
            )
            self.assertEqual(
                item.generated.evidence.release_status,
                "release_eligible_sourced_spec",
            )
            self.assertEqual(item.generated.evidence.legal_spec_id, item.legal_spec_id)
            self.assertIn("producer", item.simulation_prior_fields)
            self.assertIn("wholesale_cost", item.simulation_prior_fields)

    def test_default_generation_is_hundreds_of_strict_records(self):
        items = self.generator.generate(as_of_year=LEGAL_SNAPSHOT_AS_OF_YEAR)
        report = self.generator.report(items)
        self.assertGreaterEqual(report.records, 400)
        self.assertGreaterEqual(report.site_claim_records, 300)
        self.assertGreaterEqual(report.strict_specs_used, 15)
        self.assertGreaterEqual(report.appellations, 7)
        self.assertGreaterEqual(report.grape_identities_used, 10)

        for item in items:
            if item.wine.vineyard:
                self.assertTrue(item.generated.evidence.site_claim_eligible)
                self.assertEqual(
                    item.generated.evidence.site_claim_status,
                    "site_claim_eligible_verified_rule",
                )

    def test_prosecco_rose_uses_a_verified_legal_blend(self):
        items = self.generator.generate(
            as_of_year=LEGAL_SNAPSHOT_AS_OF_YEAR,
            include_site_claims=False,
        )
        prosecco = next(
            item for item in items if item.legal_spec_id == "it:prosecco:rose"
        )
        blend = dict(prosecco.blend_percentages)
        self.assertEqual(blend, {"Glera": 90.0, "Pinot Nero": 10.0})

    def test_release_ineligible_forced_vintage_is_rejected(self):
        with self.assertRaises(WineReleaseConstraintError):
            self.generator.generate(
                as_of_year=2026,
                vintages=[2025],
                include_site_claims=False,
            )


class DefaultCatalogEntryPointTests(unittest.TestCase):
    def test_default_loader_is_authoritative_not_legacy(self):
        wines = load_catalog(
            as_of_year=LEGAL_SNAPSHOT_AS_OF_YEAR,
            include_site_claims=False,
        )
        self.assertGreater(len(wines), 20)
        self.assertTrue(all(wine.id.startswith("strict:") for wine in wines))
        self.assertTrue(all(wine.producer.startswith("Simulation Producer ") for wine in wines))

    def test_default_loader_can_expand_verified_site_claims(self):
        base = load_catalog(
            as_of_year=LEGAL_SNAPSHOT_AS_OF_YEAR,
            include_site_claims=False,
        )
        expanded = load_catalog(
            as_of_year=LEGAL_SNAPSHOT_AS_OF_YEAR,
            include_site_claims=True,
            max_sites_per_spec=3,
        )
        self.assertGreater(len(expanded), len(base))
        self.assertTrue(any(wine.vineyard for wine in expanded))


if __name__ == "__main__":
    unittest.main()
