from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED = {
    "Muscat of Alexandria": "vivc:8241",
    "Douce Noire": "vivc:2826",
    "Trebbiano Romagnolo": "vivc:12625",
    "Palomino Fino": "vivc:8888",
    "Garganega": "vivc:4419",
    "Listán Prieto": "vivc:7873",
}


class VarietyIdentityShard0013Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_reviewed_commercial_names_resolve_r4(self):
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

    def test_prime_name_differences_do_not_create_source_aliases(self):
        for source_name in ("Corbeau Noir", "Mission"):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_muscat_family_and_trebbiano_family_stay_separate(self):
        for source_name in (
            "Muscat of Alexandria (R)",
            "Trebbiano Toscano",
            "Trebbiano Giallo",
            "Trebbiano Modenese",
        ):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            if source_name == "Trebbiano Toscano":
                self.assertTrue(decision.identity_confirmed)
                self.assertEqual(decision.canonical_id, "vivc:12628")
            else:
                self.assertFalse(decision.identity_confirmed)

    def test_r4_population_is_at_least_ten(self):
        reviewed = {
            (link.source_name, link.canonical_id)
            for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R4"
        }
        self.assertGreaterEqual(len(reviewed), 10)
        for pair in EXPECTED.items():
            self.assertIn(pair, reviewed)


if __name__ == "__main__":
    unittest.main()
