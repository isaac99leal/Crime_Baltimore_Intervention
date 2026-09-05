from __future__ import annotations

import unittest

from sommelier_v2.knowledge.national_varieties import NationalVarietyClassificationRegistry


class NationalVarietyClassificationTests(unittest.TestCase):
    def setUp(self):
        self.registry = NationalVarietyClassificationRegistry()

    def test_france_2026_classification_update_is_loaded(self):
        self.assertTrue(self.registry.is_classified("France", "Elaris"))
        self.assertTrue(self.registry.is_classified("France", "Valpesia"))
        self.assertTrue(self.registry.is_classified("France", "Bouquet 3196"))
        self.assertTrue(self.registry.is_classified("France", "Calardis blanc"))
        self.assertTrue(self.registry.is_classified("France", "Bonne Vituaigne"))

    def test_classification_does_not_claim_gi_authorization(self):
        record = self.registry.get("France", "Elaris")
        self.assertIsNotNone(record)
        self.assertEqual(record.status, "classified_wine_grape_metropolitan")
        self.assertIn("fr_legifrance_2026_07_23", record.source_ids)

    def test_registry_counts_current_france_update(self):
        stats = self.registry.stats()
        self.assertEqual(stats["national_variety_classification_countries"], 1)
        self.assertEqual(stats["national_variety_classifications"], 18)
        self.assertEqual(stats["national_variety_sources"], 2)


if __name__ == "__main__":
    unittest.main()
