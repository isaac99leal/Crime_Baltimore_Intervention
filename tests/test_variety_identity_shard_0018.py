from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED_R5 = {
    "Bical": "vivc:1568",
    "Loureiro": "vivc:6912",
    "Inzolia": "vivc:492",
}

EXPECTED_R4 = {
    "Roditis": "vivc:10141",
    "Trousseau": "vivc:12668",
}


class VarietyIdentityShard0018Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_exact_source_mappings_resolve_r5(self):
        for source_name, canonical_id in EXPECTED_R5.items():
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertTrue(decision.identity_confirmed, source_name)
            self.assertEqual(decision.status, "RESOLVED")
            self.assertEqual(decision.level, "R5")
            self.assertEqual(decision.canonical_id, canonical_id)

    def test_color_qualified_registered_names_resolve_r4(self):
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

    def test_prime_names_do_not_widen_adelaide_namespace(self):
        for source_name in ("Loureiro Blanco", "Ansonica", "Trousseau Noir"):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_related_rows_remain_separate(self):
        for source_name in ("Roditis Red", "Trousseau Gris"):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_checkpoint_counts(self):
        r5 = [
            link for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R5"
        ]
        r4 = [
            link for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R4"
        ]
        self.assertGreaterEqual(len(r5), 85)
        self.assertGreaterEqual(len(r4), 20)
        self.assertGreaterEqual(len(r5) + len(r4), 105)


if __name__ == "__main__":
    unittest.main()
