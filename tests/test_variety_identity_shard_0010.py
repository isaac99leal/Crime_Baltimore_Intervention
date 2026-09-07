from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED = {
    "Muscat Blanc à Petits Grains": "vivc:8193",
    "Fetească Albă": "vivc:4119",
    "Fetească Regală": "vivc:4121",
    "Fernão Pires": "vivc:4100",
    "Muscat Ottonel": "vivc:8243",
    "Moldova": "vivc:7896",
    "Isabella": "vivc:5560",
}


class VarietyIdentityShard0010Tests(unittest.TestCase):
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

    def test_muscat_color_and_family_rows_do_not_collapse(self):
        alexandria = self.registry.resolve("Muscat of Alexandria", source_id="adelaide_2025")
        self.assertTrue(alexandria.identity_confirmed)
        self.assertEqual(alexandria.canonical_id, "vivc:8241")
        self.assertNotEqual(alexandria.canonical_id, "vivc:8193")

        hamburg = self.registry.resolve("Muscat of Hamburg", source_id="adelaide_2025")
        self.assertTrue(hamburg.identity_confirmed)
        self.assertEqual(hamburg.canonical_id, "vivc:8226")
        self.assertNotEqual(hamburg.canonical_id, "vivc:8193")

        decision = self.registry.resolve("Muscat Blanc à Petits Grains (R)", source_id="adelaide_2025")
        self.assertFalse(decision.identity_confirmed)
        self.assertIsNone(decision.canonical_id)

    def test_feteasca_rows_remain_distinct(self):
        alba = self.registry.resolve("Fetească Albă", source_id="adelaide_2025")
        regala = self.registry.resolve("Fetească Regală", source_id="adelaide_2025")
        self.assertNotEqual(alba.canonical_id, regala.canonical_id)
        self.assertEqual(
            self.registry.resolve("Fetească Neagră", source_id="adelaide_2025").status,
            "UNKNOWN",
        )

    def test_interspecific_identity_is_not_vinifera_inferred(self):
        for source_name, canonical_id in (("Moldova", "vivc:7896"), ("Isabella", "vivc:5560")):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertEqual(decision.canonical_id, canonical_id)
            self.assertEqual(self.registry.identities[canonical_id]["species"], "interspecific cross")

    def test_reviewed_adelaide_population_is_at_least_80(self):
        reviewed = {
            (link.source_name, link.canonical_id)
            for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R5"
        }
        self.assertGreaterEqual(len(reviewed), 80)
        for pair in EXPECTED.items():
            self.assertIn(pair, reviewed)


if __name__ == "__main__":
    unittest.main()
