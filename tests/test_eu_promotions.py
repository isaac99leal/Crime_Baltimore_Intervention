from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sommelier_v2.knowledge.eu_promotions import (
    EuLegalPromotionRegistry,
    VerificationLevel,
)
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.machine_legal_constraints import MachineLegalConstraintRegistry


class EuPromotionTests(unittest.TestCase):
    def registry(self, allowed_grapes):
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name) / "machine.json"
        path.write_text(json.dumps([{
            "gi_identifier": "EUGI00000099999",
            "file_number": "PDO-XX-A9999",
            "protected_names": ["Example PDO"],
            "countries": ["XX"],
            "gi_type": "PDO",
            "allowed_grapes": allowed_grapes,
            "constraint_level": "deny_only",
            "extraction_status": "explicit_variety_section_extracted",
            "source_attachment_id": "777",
            "source_url": "https://example.invalid/777",
            "section_sha256": "abc123",
        }]), encoding="utf-8")
        machine = MachineLegalConstraintRegistry(path)
        self.addCleanup(tmp.cleanup)
        return EuLegalPromotionRegistry(machine), machine.records[0]

    def test_single_grape_section_promotes_composition_dimension(self):
        promotions, record = self.registry(["Barbera"])
        self.assertEqual(promotions.level(record), VerificationLevel.COMPOSITION_VERIFIED)
        decision = promotions.evaluate_composition(record, {"Barbera": 100})
        self.assertTrue(decision.verified)
        self.assertEqual(decision.status, "composition_verified_full_spec_pending")
        self.assertIn("section_sha256:abc123", decision.evidence)

    def test_single_grape_promotion_rejects_outsider(self):
        promotions, record = self.registry(["Barbera"])
        decision = promotions.evaluate_composition(record, {"Nebbiolo": 100})
        self.assertFalse(decision.verified)
        self.assertEqual(decision.status, "grape_not_permitted_machine_extracted")

    def test_multi_grape_section_stays_deny_safe_only(self):
        promotions, record = self.registry(["Tempranillo", "Garnacha"])
        self.assertEqual(promotions.level(record), VerificationLevel.DENY_SAFE)
        decision = promotions.evaluate_composition(record, {"Tempranillo": 100})
        self.assertFalse(decision.verified)
        self.assertEqual(decision.status, "composition_not_complete_enough_to_promote")

    def test_materialized_snapshot_has_promotable_single_grape_rules(self):
        stats = EuLegalPromotionRegistry().stats()
        self.assertGreaterEqual(stats["eu_machine_source_records"], 1000)
        self.assertGreaterEqual(stats["eu_machine_deny_safe_or_better"], 400)
        self.assertGreater(stats["eu_machine_composition_verified_records"], 0)


class StrictSupplementTests(unittest.TestCase):
    def setUp(self):
        self.registry = LegalSpecRegistry()

    def test_nizza_is_strict_100_percent_barbera(self):
        standard = self.registry.resolve(country="Italy", appellation="Nizza DOCG")
        riserva = self.registry.resolve(country="Italy", appellation="Nizza DOCG", variant="riserva")
        self.assertIsNotNone(standard)
        self.assertIsNotNone(riserva)
        self.assertTrue(self.registry.evaluate_blend(standard, {"Barbera": 100}).eligible)
        self.assertFalse(self.registry.evaluate_blend(standard, {"Barbera": 95, "Nebbiolo": 5}).eligible)
        self.assertEqual(standard.max_yield_t_ha, 7.0)
        self.assertEqual(standard.min_total_aging_months, 18)
        self.assertEqual(riserva.min_total_aging_months, 30)
        self.assertEqual(riserva.min_wood_aging_months, 12)

    def test_morellino_safe_100_percent_sangiovese_paths(self):
        standard = self.registry.resolve(country="Italy", appellation="Morellino di Scansano DOCG")
        riserva = self.registry.resolve(
            country="Italy", appellation="Morellino di Scansano DOCG", variant="riserva"
        )
        superiore = self.registry.resolve(
            country="Italy", appellation="Morellino di Scansano DOCG", variant="superiore"
        )
        self.assertIsNotNone(standard)
        self.assertIsNotNone(riserva)
        self.assertIsNotNone(superiore)
        self.assertTrue(self.registry.evaluate_blend(standard, {"Sangiovese": 100}).eligible)
        self.assertTrue(self.registry.evaluate_blend(riserva, {"Sangiovese": 100}).eligible)
        self.assertFalse(self.registry.evaluate_blend(standard, {"Merlot": 100}).eligible)
        self.assertEqual(standard.max_yield_t_ha, 9.0)
        self.assertEqual(riserva.max_yield_t_ha, 8.0)
        self.assertEqual(riserva.min_total_aging_months, 24)
        self.assertEqual(riserva.min_wood_aging_months, 12)
        self.assertEqual(superiore.release_year_offset, 2)

    def test_strict_registry_expands_beyond_seed(self):
        stats = self.registry.stats()
        self.assertGreaterEqual(stats["sourced_legal_wine_specs"], 21)
        self.assertGreaterEqual(stats["sourced_appellations_with_strict_specs"], 9)


if __name__ == "__main__":
    unittest.main()
