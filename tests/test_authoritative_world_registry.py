from __future__ import annotations

import unittest

from sommelier_v2.wine_registry import SommelierWorldRegistry


class AuthoritativeWorldRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = SommelierWorldRegistry.build(
            target_count=60,
            seed=999,
            strict_origin=False,
            as_of_year=2026,
            include_site_claims=True,
        )

    def test_default_registry_has_one_market_with_two_object_views(self):
        self.assertEqual(len(self.registry.v2_wines), 60)
        self.assertEqual(len(self.registry.legacy_wines), 60)
        self.assertEqual(len(self.registry), 60)
        self.assertTrue(all(wine.id.startswith("strict:") for wine in self.registry.v2_wines))

        for record, legacy in zip(self.registry.v2_wines, self.registry.legacy_wines):
            self.assertEqual(legacy.id, record.id)
            self.assertEqual(legacy.vintage, record.vintage)
            self.assertEqual(legacy.appellation, record.appellation)
            self.assertEqual(legacy.vineyard_name, record.vineyard)
            self.assertEqual(legacy.producer_name, record.producer)

    def test_legacy_compatibility_view_preserves_exact_authoritative_blend(self):
        for record, legacy in zip(self.registry.v2_wines, self.registry.legacy_wines):
            self.assertAlmostEqual(
                sum(component.percentage for component in legacy.grapes),
                100.0,
                places=6,
            )
            self.assertEqual(
                tuple(component.grape for component in legacy.grapes),
                record.grapes,
            )

    def test_old_strict_origin_escape_hatch_cannot_disable_default_validation(self):
        # ``strict_origin=False`` is intentionally ignored on the unified default
        # registry. It remains in the signature only so old callers do not break.
        self.assertTrue(
            all(wine.id.startswith("strict:") for wine in self.registry.v2_wines)
        )

    def test_legacy_database_helpers_remain_available_without_generating_wines(self):
        self.assertIsNotNone(self.registry.region_db)
        self.assertIsNotNone(self.registry.grape_db)
        self.assertGreater(len(self.registry.knowledge.grapes), 1000)

    def test_registry_stats_distinguish_authority_from_compatibility_view(self):
        stats = self.registry.stats()
        self.assertEqual(stats["unified_registry_authoritative_market_records"], 60)
        self.assertEqual(stats["unified_registry_legacy_compatibility_views"], 60)
        self.assertEqual(stats["unified_registry_v2_market_records"], 60)


if __name__ == "__main__":
    unittest.main()
