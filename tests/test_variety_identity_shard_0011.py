from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED = {
    "Mazuelo": "vivc:2098",
    "Prosecco": "vivc:9741",
}


class VarietyIdentityShard0011Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_reviewed_synonyms_resolve_r4(self):
        for source_name, canonical_id in EXPECTED.items():
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertTrue(decision.identity_confirmed, source_name)
            self.assertEqual(decision.status, "RESOLVED")
            self.assertEqual(decision.level, "R4")
            self.assertEqual(decision.canonical_id, canonical_id)

    def test_source_scope_stays_closed(self):
        for source_name in EXPECTED:
            self.assertEqual(
                self.registry.resolve(source_name, source_id="another-census").status,
                "UNKNOWN",
            )

    def test_prime_names_do_not_become_adelaide_aliases(self):
        for name in ("Carignan Noir", "Glera"):
            decision = self.registry.resolve(name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_prosecco_lungo_stays_separate(self):
        decision = self.registry.resolve("Prosecco Lungo", source_id="adelaide_2025")
        self.assertFalse(decision.identity_confirmed)
        self.assertIsNone(decision.canonical_id)

    def test_r4_and_r5_counts_are_distinct(self):
        r4 = [
            link for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R4"
        ]
        r5 = [
            link for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R5"
        ]
        self.assertGreaterEqual(len(r4), 2)
        self.assertGreaterEqual(len(r5), 80)


if __name__ == "__main__":
    unittest.main()
