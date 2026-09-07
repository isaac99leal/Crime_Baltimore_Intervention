from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED = {
    "Montepulciano": "vivc:7949",
    "Nero d'Avola": "vivc:1986",
    "Aligoté": "vivc:312",
    "Touriga Franca": "vivc:12593",
    "Touriga Nacional": "vivc:12594",
    "Alvarinho": "vivc:15689",
    "Aglianico": "vivc:121",
    "Ancellotta": "vivc:447",
    "Furmint": "vivc:4292",
    "Agiorgitiko": "vivc:102",
    "Godello": "vivc:4840",
    "Assyrtiko": "vivc:726",
}


class VarietyIdentityShard0007Tests(unittest.TestCase):
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

    def test_prime_name_and_synonym_differences_do_not_widen_source_namespace(self):
        alias_pairs = {
            "Nero d'Avola": "Calabrese",
            "Godello": "Godelho",
            "Alvarinho": "Albariño",
        }
        for source_name, authority_or_synonym_name in alias_pairs.items():
            self.assertTrue(
                self.registry.resolve(source_name, source_id="adelaide_2025").identity_confirmed
            )
            self.assertEqual(
                self.registry.resolve(
                    authority_or_synonym_name,
                    source_id="adelaide_2025",
                ).status,
                "UNKNOWN",
            )

    def test_related_source_rows_are_not_collapsed(self):
        for source_name in ("Asirtiko Red", "Aglianicone", "Touriga Femea"):
            self.assertEqual(
                self.registry.resolve(source_name, source_id="adelaide_2025").status,
                "UNKNOWN",
            )

    def test_diacritic_fold_remains_candidate_only(self):
        exact = self.registry.resolve("Aligoté", source_id="adelaide_2025")
        folded = self.registry.resolve("Aligote", source_id="adelaide_2025")
        self.assertTrue(exact.identity_confirmed)
        self.assertEqual(folded.status, "CANDIDATE")
        self.assertEqual(folded.level, "R2")
        self.assertIsNone(folded.canonical_id)

    def test_reviewed_adelaide_population_is_at_least_60(self):
        reviewed = {
            (link.source_name, link.canonical_id)
            for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R5"
        }
        self.assertGreaterEqual(len(reviewed), 60)
        for pair in EXPECTED.items():
            self.assertIn(pair, reviewed)


if __name__ == "__main__":
    unittest.main()
