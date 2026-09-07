from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


class VarietyIdentityShard0017Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_durif_resolves_as_reviewed_r4(self):
        decision = self.registry.resolve("Durif", source_id="adelaide_2025")
        self.assertTrue(decision.identity_confirmed)
        self.assertEqual(decision.status, "RESOLVED")
        self.assertEqual(decision.level, "R4")
        self.assertEqual(decision.canonical_id, "vivc:3738")

    def test_durif_synonyms_do_not_widen_adelaide_namespace(self):
        for source_name in ("Petite Sirah", "Petite Syrah"):
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertFalse(decision.identity_confirmed)
            self.assertIsNone(decision.canonical_id)

    def test_durif_source_scope_stays_closed(self):
        self.assertEqual(
            self.registry.resolve("Durif", source_id="another-census").status,
            "UNKNOWN",
        )

    def test_checkpoint_reaches_one_hundred_strong_links(self):
        strong = [
            link for link in self.registry.links
            if link.source_id == "adelaide_2025" and link.level in {"R4", "R5"}
        ]
        self.assertGreaterEqual(len(strong), 100)
        self.assertGreaterEqual(
            len([link for link in strong if link.level == "R4"]), 18
        )
        self.assertGreaterEqual(
            len([link for link in strong if link.level == "R5"]), 82
        )


if __name__ == "__main__":
    unittest.main()
