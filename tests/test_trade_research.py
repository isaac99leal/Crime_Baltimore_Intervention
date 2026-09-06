from __future__ import annotations

import unittest

from sommelier_v2.knowledge.trade_research import TradeResearchError, TradeResearchRegistry


class TradeResearchRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = TradeResearchRegistry()

    def test_recovered_trade_corpus_keeps_scale(self):
        stats = self.registry.stats()
        self.assertEqual(stats.source_count, 33)
        self.assertGreaterEqual(stats.observation_count, 43)
        self.assertGreaterEqual(stats.technical_field_count, 410)
        self.assertGreaterEqual(stats.country_count, 8)
        self.assertGreaterEqual(stats.producer_count, 25)

    def test_every_observation_resolves_to_verified_source(self):
        for observation in self.registry.observations:
            source = self.registry.source(observation.trade_source_id)
            self.assertIsNotNone(source)
            self.assertEqual(observation.source_ref, source.source_ref)
            self.assertTrue(observation.source_url.startswith(("https://", "http://")))
            self.assertGreater(observation.technical_field_count, 0)

    def test_trade_evidence_cannot_promote_legal_genetic_or_weather_authority(self):
        for claim in (
            "protectedOriginLegalStatus",
            "authorizedGrapeLegality",
            "primeCultivarIdentity",
            "geneticParentage",
            "historicalWeather",
            "officialVintageRating",
        ):
            with self.assertRaises(TradeResearchError):
                self.registry.assert_trade_can_support(claim)

        self.registry.assert_trade_can_support("fermentationVessel")
        self.registry.assert_trade_can_support("harvestMethod")

    def test_vintage_trajectory_is_not_collapsed(self):
        trajectory = self.registry.trajectory("Cara Sur", "Criolla Chica")
        self.assertGreaterEqual(len(trajectory), 2)
        self.assertEqual([obs.vintage for obs in trajectory[:2]], [2018, 2022])
        self.assertEqual(trajectory[0].field("maturationVessel"), "Concrete Egg")
        self.assertEqual(trajectory[1].field("maturationVessel"), "Concrete Vats")
        self.assertNotEqual(
            trajectory[0].field("productionQuantityCases12"),
            trajectory[1].field("productionQuantityCases12"),
        )

    def test_observation_fields_are_immutable(self):
        observation = self.registry.observations[0]
        with self.assertRaises(TypeError):
            observation.fields["invented"] = "not allowed"  # type: ignore[index]

    def test_same_vintage_conflicts_are_preserved_not_overwritten(self):
        conflicts = self.registry.same_vintage_conflicts()
        for conflict in conflicts:
            self.assertGreaterEqual(len(conflict.observation_ids), 2)
            self.assertGreaterEqual(len(conflict.serialized_values), 2)


if __name__ == "__main__":
    unittest.main()
