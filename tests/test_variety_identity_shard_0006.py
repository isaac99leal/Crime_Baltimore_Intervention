from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED = {
    "Xarello": "vivc:13270",
    "Savatiano": "vivc:10798",
    "Grillo": "vivc:5021",
    "Zweigelt": "vivc:13484",
    "Castelão": "vivc:9152",
    "Baga": "vivc:885",
    "Pinotage": "vivc:9286",
    "Chasselas": "vivc:2473",
    "Caladoc": "vivc:1989",
    "Carmenère": "vivc:2109",
}


class VarietyIdentityShard0006Tests(unittest.TestCase):
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

    def test_registry_prime_names_do_not_create_adelaide_aliases(self):
        alias_pairs = {
            "Xarello": "Xarel·lo",
            "Savatiano": "Savvatiano",
            "Zweigelt": "Rotburger",
            "Castelão": "Periquita",
        }
        for source_name, authority_or_synonym_name in alias_pairs.items():
            self.assertTrue(
                self.registry.resolve(source_name, source_id="adelaide_2025").identity_confirmed
            )
            decision = self.registry.resolve(authority_or_synonym_name, source_id="adelaide_2025")
            # Punctuation folding can suggest Xarello, but cannot confirm an alias.
            self.assertEqual(decision.status, "CANDIDATE" if source_name == "Xarello" else "UNKNOWN")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)
            if source_name == "Xarello":
                self.assertEqual(decision.level, "R2")
                self.assertEqual(decision.candidate_ids, ("vivc:13270",))

    def test_diacritic_fold_is_candidate_not_reviewed_identity(self):
        exact = self.registry.resolve("Carmenère", source_id="adelaide_2025")
        folded = self.registry.resolve("Carmenere", source_id="adelaide_2025")
        self.assertTrue(exact.identity_confirmed)
        self.assertEqual(folded.status, "CANDIDATE")
        self.assertEqual(folded.level, "R2")
        self.assertIsNone(folded.canonical_id)

    def test_related_chasselas_source_row_is_not_collapsed(self):
        self.assertTrue(
            self.registry.resolve("Chasselas", source_id="adelaide_2025").identity_confirmed
        )
        self.assertEqual(
            self.registry.resolve("Chasselas (R)", source_id="adelaide_2025").status,
            "UNKNOWN",
        )

    def test_known_conflicted_or_underspecified_rows_remain_unknown(self):
        for source_name in ("Petit Verdot", "Alicante Bouschet", "Catarratto Bianco"):
            self.assertEqual(
                self.registry.resolve(source_name, source_id="adelaide_2025").status,
                "UNKNOWN",
            )

    def test_exact_reviewed_adelaide_r5_population_is_at_least_48(self):
        reviewed = {
            (link.source_name, link.canonical_id)
            for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R5"
        }
        self.assertGreaterEqual(len(reviewed), 48)
        for pair in EXPECTED.items():
            self.assertIn(pair, reviewed)


if __name__ == "__main__":
    unittest.main()
