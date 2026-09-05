from __future__ import annotations

import unittest

from sommelier_v2.knowledge import (
    LegalAwareRegionGrapeRulebook,
    NationalAwareLegalSpecRegistry,
    NationalLegalOverrideRegistry,
)


class NationalOverrideTests(unittest.TestCase):
    def test_override_registry_has_effective_and_pending_records(self):
        registry = NationalLegalOverrideRegistry()
        stats = registry.stats()
        self.assertGreaterEqual(stats["national_legal_effective_records"], 10)
        self.assertGreaterEqual(stats["national_legal_pending_records"], 2)
        self.assertEqual(stats["national_legal_override_countries"], 3)

    def test_current_national_source_is_attached_to_barolo(self):
        registry = NationalAwareLegalSpecRegistry()
        spec = registry.resolve(
            country="Italy", appellation="Barolo DOCG", variant="standard"
        )
        self.assertIsNotNone(spec)
        self.assertIn("national_it_barolo_masaf_2026", spec.source_ids)
        self.assertEqual(spec.max_yield_t_ha, 8.0)
        self.assertEqual(spec.min_potential_alcohol_pct, 12.5)

    def test_pending_2026_champagne_change_does_not_override_current_law(self):
        registry = NationalAwareLegalSpecRegistry()
        spec = registry.resolve(
            country="France", appellation="Champagne AOP", variant="standard"
        )
        self.assertIsNotNone(spec)
        # Current effective seed remains 5%. The pending 2026 proposal is
        # recorded in the override registry but is not applied as law.
        self.assertEqual(spec.vineyard_adaptation_max_pct, 5.0)
        self.assertIn("national_fr_champagne_inao_effective_2025", spec.source_ids)
        self.assertNotIn("national_fr_champagne_inao_pending_2026", spec.source_ids)

    def test_public_legal_rulebook_uses_national_aware_registry(self):
        rules = LegalAwareRegionGrapeRulebook()
        self.assertIsInstance(rules.legal_specs, NationalAwareLegalSpecRegistry)
        stats = rules.stats()
        self.assertGreaterEqual(stats["national_legal_effective_records"], 10)


if __name__ == "__main__":
    unittest.main()
