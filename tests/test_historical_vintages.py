from __future__ import annotations

import unittest

from sommelier_v2.knowledge.historical_vintages import HistoricalVintageError, HistoricalVintageRegistry


class HistoricalVintageRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = HistoricalVintageRegistry()

    def test_recovered_corpus_scale(self):
        stats = self.registry.stats()
        self.assertEqual(stats.observation_count, 17)
        self.assertEqual(stats.authority_rating_count, 25)
        self.assertEqual(stats.archive_count, 4)
        self.assertGreaterEqual(stats.country_count, 7)
        self.assertGreaterEqual(stats.region_count, 9)
        self.assertLessEqual(stats.earliest_observation_year, 2020)
        self.assertGreaterEqual(stats.latest_observation_year, 2025)

    def test_exact_years_keep_distinct_signals(self):
        bordeaux_2021 = self.registry.observation("France", "Bordeaux", 2021)
        bordeaux_2022 = self.registry.observation("France", "Bordeaux", 2022)
        self.assertIsNotNone(bordeaux_2021)
        self.assertIsNotNone(bordeaux_2022)
        assert bordeaux_2021 is not None and bordeaux_2022 is not None

        self.assertNotEqual(bordeaux_2021.signal.ripeness, bordeaux_2022.signal.ripeness)
        self.assertNotEqual(bordeaux_2021.signal.acidity, bordeaux_2022.signal.acidity)
        self.assertNotEqual(bordeaux_2021.signal.disease_pressure, bordeaux_2022.signal.disease_pressure)
        self.assertNotEqual(bordeaux_2021.growing_season, bordeaux_2022.growing_season)

    def test_all_simulation_modifiers_are_explicitly_bounded(self):
        for observation in self.registry.observations:
            self.assertGreaterEqual(observation.signal.confidence, 1)
            self.assertLessEqual(observation.signal.confidence, 5)
            for value in observation.signal.as_dict().values():
                self.assertGreaterEqual(value, -1.0)
                self.assertLessEqual(value, 1.0)
            self.assertTrue(observation.source_refs)

    def test_narrative_evidence_does_not_fabricate_daily_weather(self):
        observation = self.registry.observation("Germany", "Mosel", 2023)
        self.assertIsNotNone(observation)
        assert observation is not None
        with self.assertRaises(HistoricalVintageError):
            observation.require_daily_weather()

    def test_authority_rating_stays_categorical_and_source_linked(self):
        ratings = self.registry.authority_rating("Rioja DOCa", 2025)
        self.assertEqual(len(ratings), 1)
        self.assertEqual(ratings[0].rating, "Excellent")
        self.assertTrue(ratings[0].source_refs)

    def test_archive_year_inclusion_is_explicit_not_range_inferred(self):
        port = self.registry.archive("archive-pt-vintage-port-1756-2017")
        self.assertIsNotNone(port)
        assert port is not None
        self.assertTrue(port.explicitly_lists(1756))
        self.assertTrue(port.explicitly_lists(2017))
        self.assertFalse(port.explicitly_lists(2015))

        champagne = self.registry.archive("archive-fr-champagne-matu-monitoring-1956-present")
        self.assertIsNotNone(champagne)
        assert champagne is not None
        self.assertEqual(champagne.earliest_year, 1956)
        self.assertEqual(champagne.years, ())
        self.assertFalse(champagne.explicitly_lists(2000))

    def test_national_archive_is_not_silently_regionalized(self):
        south_africa = self.registry.archive("archive-za-harvest-reports-2002-2026")
        self.assertIsNotNone(south_africa)
        assert south_africa is not None
        self.assertIn("national", south_africa.modern_geographic_reference.lower())
        self.assertTrue(south_africa.explicitly_lists(2021))


if __name__ == "__main__":
    unittest.main()
