from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


EXPECTED = {
    "Bobal": "vivc:1493",
    "Cayetana Blanca": "vivc:5648",
    "Colombard": "vivc:2771",
    "Graševina": "vivc:13217",
    "Blaufränkisch": "vivc:1459",
    "Gewürztraminer": "vivc:12609",
    "Mencía": "vivc:7623",
    "Vranac": "vivc:13179",
    "Marselan": "vivc:16383",
}


class VarietyIdentityShard0005Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_all_exact_adelaide_names_resolve_r5(self):
        for source_name, canonical_id in EXPECTED.items():
            decision = self.registry.resolve(source_name, source_id="adelaide_2025")
            self.assertTrue(decision.identity_confirmed, source_name)
            self.assertEqual(decision.level, "R5")
            self.assertEqual(decision.canonical_id, canonical_id)

    def test_source_scope_stays_closed(self):
        for source_name in EXPECTED:
            self.assertEqual(
                self.registry.resolve(source_name, source_id="another-census").status,
                "UNKNOWN",
            )

    def test_prime_name_difference_does_not_create_adelaide_alias(self):
        self.assertTrue(
            self.registry.resolve("Cayetana Blanca", source_id="adelaide_2025").identity_confirmed
        )
        self.assertEqual(
            self.registry.resolve("Jaen Blanco", source_id="adelaide_2025").status,
            "UNKNOWN",
        )
        self.assertTrue(
            self.registry.resolve("Graševina", source_id="adelaide_2025").identity_confirmed
        )
        self.assertEqual(
            self.registry.resolve("Welschriesling", source_id="adelaide_2025").status,
            "UNKNOWN",
        )

    def test_umbrella_catarratto_row_remains_unresolved(self):
        self.assertEqual(
            self.registry.resolve("Catarratto Bianco", source_id="adelaide_2025").status,
            "UNKNOWN",
        )


if __name__ == "__main__":
    unittest.main()
