from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED = {
    "Cereza": "vivc:2390",
    "Criolla Grande": "vivc:3241",
    "Torrontés Riojano": "vivc:15162",
    "Pedro Giménez": "vivc:24977",
}


class VarietyIdentityShard0019Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_peer_reviewed_genotype_rows_are_r3_candidates_only(self):
        for source_name, canonical_id in EXPECTED.items():
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertEqual(decision.status, "CANDIDATE", source_name)
            self.assertEqual(decision.level, "R3")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)
            self.assertEqual(decision.candidate_ids, (canonical_id,))

    def test_source_scope_stays_closed(self):
        for source_name in EXPECTED:
            self.assertEqual(
                self.registry.resolve(source_name, source_id="another-census").status,
                "UNKNOWN",
            )

    def test_pedro_gimenez_does_not_collapse_into_pedro_ximenez(self):
        gimenez = self.registry.resolve("Pedro Giménez", source_id="adelaide_2025")
        ximenez = self.registry.resolve("Pedro Ximénez", source_id="adelaide_2025")
        self.assertEqual(gimenez.level, "R3")
        self.assertTrue(ximenez.identity_confirmed)
        self.assertEqual(ximenez.canonical_id, "vivc:9080")
        self.assertNotIn("vivc:9080", gimenez.candidate_ids)

    def test_torrontes_family_is_not_root_name_collapsed(self):
        riojano = self.registry.resolve("Torrontés Riojano", source_id="adelaide_2025")
        self.assertEqual(riojano.candidate_ids, ("vivc:15162",))
        for source_name in ("Torrontés", "Torrontés Sanjuanino", "Torrontes Mendocino"):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)

    def test_r3_population_is_at_least_four(self):
        r3 = [
            link for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level == "R3"
        ]
        self.assertGreaterEqual(len(r3), 4)


if __name__ == "__main__":
    unittest.main()
