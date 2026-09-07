from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED = {
    "Trebbiano Toscano": "vivc:12628",
    "Alicante Henri Bouschet": "vivc:304",
}


class VarietyIdentityShard0012Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_high_area_reviewed_names_resolve_r4(self):
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

    def test_trebbiano_related_rows_do_not_collapse(self):
        for source_name in (
            "Trebbiano Romagnolo",
            "Trebbiano Giallo",
            "Trebbiano Modenese",
            "Trebbiano Spoletino",
        ):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_alicante_bouschet_homonym_is_not_borrowed(self):
        decision = self.registry.resolve("Alicante Bouschet", source_id="adelaide_2025")
        self.assertFalse(decision.identity_confirmed)
        self.assertIsNone(decision.canonical_id)

    def test_reviewed_r4_population_is_at_least_four(self):
        reviewed = {
            (link.source_name, link.canonical_id)
            for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R4"
        }
        self.assertGreaterEqual(len(reviewed), 4)
        for pair in EXPECTED.items():
            self.assertIn(pair, reviewed)


if __name__ == "__main__":
    unittest.main()
