from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED_R5 = {
    "Nebbiolo": "vivc:8417",
    "Dornfelder": "vivc:3659",
}

EXPECTED_R4 = {
    "Arinto de Bucelas": "vivc:602",
    "Corvina Veronese": "vivc:2863",
}


class VarietyIdentityShard0016Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_exact_registered_names_resolve_r5(self):
        for source_name, canonical_id in EXPECTED_R5.items():
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertTrue(decision.identity_confirmed, source_name)
            self.assertEqual(decision.status, "RESOLVED")
            self.assertEqual(decision.level, "R5")
            self.assertEqual(decision.canonical_id, canonical_id)

    def test_reviewed_canonical_name_propositions_resolve_r4(self):
        for source_name, canonical_id in EXPECTED_R4.items():
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertTrue(decision.identity_confirmed, source_name)
            self.assertEqual(decision.status, "RESOLVED")
            self.assertEqual(decision.level, "R4")
            self.assertEqual(decision.canonical_id, canonical_id)

    def test_source_scope_stays_closed(self):
        for source_name in (*EXPECTED_R5, *EXPECTED_R4):
            self.assertEqual(
                self.registry.resolve(source_name, source_id="another-census").status,
                "UNKNOWN",
            )

    def test_authority_registered_components_do_not_create_adelaide_aliases(self):
        for source_name in ("Arinto", "Corvina"):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_corvinone_is_not_corvina(self):
        decision = self.registry.resolve("Corvinone", source_id="adelaide_2025")
        self.assertFalse(decision.identity_confirmed)
        self.assertIsNone(decision.canonical_id)

    def test_checkpoint_counts(self):
        r5 = {
            (link.source_name, link.canonical_id)
            for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R5"
        }
        r4 = {
            (link.source_name, link.canonical_id)
            for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R4"
        }
        self.assertGreaterEqual(len(r5), 82)
        self.assertGreaterEqual(len(r4), 17)
        for pair in EXPECTED_R5.items():
            self.assertIn(pair, r5)
        for pair in EXPECTED_R4.items():
            self.assertIn(pair, r4)


if __name__ == "__main__":
    unittest.main()
