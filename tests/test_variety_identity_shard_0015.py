from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED_R4 = {
    "Muscat of Hamburg": "vivc:8226",
    "Côt": "vivc:2889",
    "Tribidrag": "vivc:9703",
}


class VarietyIdentityShard0015Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_reviewed_names_resolve_r4(self):
        for source_name, canonical_id in EXPECTED_R4.items():
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertTrue(decision.identity_confirmed, source_name)
            self.assertEqual(decision.status, "RESOLVED")
            self.assertEqual(decision.level, "R4")
            self.assertEqual(decision.canonical_id, canonical_id)

    def test_source_scope_stays_closed(self):
        for source_name in EXPECTED_R4:
            self.assertEqual(
                self.registry.resolve(source_name, source_id="another-census").status,
                "UNKNOWN",
            )

    def test_authority_prime_names_do_not_widen_adelaide_namespace(self):
        for source_name in ("Muscat Hamburg", "Cot", "Malbec", "Primitivo", "Zinfandel"):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_muscat_family_stays_separate(self):
        hamburg = self.registry.resolve("Muscat of Hamburg", source_id="adelaide_2025")
        alexandria = self.registry.resolve("Muscat of Alexandria", source_id="adelaide_2025")
        petits = self.registry.resolve("Muscat Blanc à Petits Grains", source_id="adelaide_2025")
        self.assertEqual(hamburg.canonical_id, "vivc:8226")
        self.assertEqual(alexandria.canonical_id, "vivc:8241")
        self.assertEqual(petits.canonical_id, "vivc:8193")
        self.assertEqual(len({hamburg.canonical_id, alexandria.canonical_id, petits.canonical_id}), 3)

    def test_tribidrag_does_not_collapse_related_adelaide_rows(self):
        for source_name in ("Primitivo", "Zinfandel"):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)

    def test_r4_population_is_at_least_fifteen(self):
        reviewed = {
            (link.source_name, link.canonical_id)
            for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R4"
        }
        self.assertGreaterEqual(len(reviewed), 15)
        for pair in EXPECTED_R4.items():
            self.assertIn(pair, reviewed)


if __name__ == "__main__":
    unittest.main()
