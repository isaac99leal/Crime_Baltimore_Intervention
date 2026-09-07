from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED = {
    "Verdejo": "vivc:12949",
    "Pinot Meunier": "vivc:9278",
    "Müller-Thurgau": "vivc:8141",
    "Sémillon": "vivc:11480",
    "Negroamaro": "vivc:8456",
    "Pedro Ximénez": "vivc:9080",
}


class VarietyIdentityShard0008Tests(unittest.TestCase):
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

    def test_prime_names_and_synonyms_do_not_widen_adelaide_namespace(self):
        for alias in (
            "Verdejo Blanco",
            "Meunier",
            "Schwarzriesling",
            "Mueller Thurgau",
            "Negro Amaro",
            "Pedro Ximenes",
        ):
            decision = self.registry.resolve(alias, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_diacritic_and_punctuation_folds_are_candidates_only(self):
        for exact_name, folded_name in (
            ("Müller-Thurgau", "Muller-Thurgau"),
            ("Sémillon", "Semillon"),
            ("Pedro Ximénez", "Pedro Ximenez"),
        ):
            self.assertTrue(
                self.registry.resolve(exact_name, source_id="adelaide_2025").identity_confirmed
            )
            folded = self.registry.resolve(folded_name, source_id="adelaide_2025")
            self.assertEqual(folded.status, "CANDIDATE")
            self.assertEqual(folded.level, "R2")
            self.assertIsNone(folded.canonical_id)

    def test_related_rows_do_not_collapse(self):
        for source_name in ("Negroamaro Precoce", "Pedro Giménez"):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_reviewed_adelaide_population_is_at_least_66(self):
        reviewed = {
            (link.source_name, link.canonical_id)
            for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R5"
        }
        self.assertGreaterEqual(len(reviewed), 66)
        for pair in EXPECTED.items():
            self.assertIn(pair, reviewed)


if __name__ == "__main__":
    unittest.main()
