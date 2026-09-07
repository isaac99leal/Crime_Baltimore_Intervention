from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED = {
    "Parellada": "vivc:8938",
    "Tannat": "vivc:12257",
    "Tinta Barroca": "vivc:12462",
    "Trincadeira": "vivc:15685",
    "Rabigato": "vivc:9857",
    "Pecorino": "vivc:9072",
    "Passerina": "vivc:6413",
}


class VarietyIdentityShard0009Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_all_exact_adelaide_names_resolve_r5(self):
        for source_name, canonical_id in EXPECTED.items():
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertTrue(decision.identity_confirmed, source_name)
            self.assertEqual(decision.status, "RESOLVED")
            self.assertEqual(decision.level, "R5")
            self.assertEqual(decision.canonical_id, canonical_id)

    def test_source_scope_stays_closed(self):
        for source_name in EXPECTED:
            self.assertEqual(
                self.registry.resolve(source_name, source_id="another-census").status,
                "UNKNOWN",
            )

    def test_prime_name_differences_do_not_widen_source_namespace(self):
        for alias in ("Trincadeira Preta",):
            decision = self.registry.resolve(alias, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_related_rows_remain_separate(self):
        for source_name in ("Rabigato Moreno", "Pecorello"):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_unreviewed_spelling_variants_are_not_promoted(self):
        for source_name in ("Tanat", "Parellada B"):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_reviewed_adelaide_population_is_at_least_73(self):
        reviewed = {
            (link.source_name, link.canonical_id)
            for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R5"
        }
        self.assertGreaterEqual(len(reviewed), 73)
        for pair in EXPECTED.items():
            self.assertIn(pair, reviewed)


if __name__ == "__main__":
    unittest.main()
