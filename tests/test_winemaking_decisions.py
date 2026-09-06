from __future__ import annotations

import unittest

from sommelier_v2.knowledge.winemaking_decisions import (
    WinemakingDecisionError,
    WinemakingDecisionRegistry,
)


class WinemakingDecisionRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = WinemakingDecisionRegistry()

    def test_recovered_decision_matrix_scale(self):
        stats = self.registry.stats()
        self.assertEqual(stats.decision_count, 51)
        self.assertEqual(stats.axis_count, 16)
        self.assertGreaterEqual(stats.option_count, 140)
        self.assertGreaterEqual(stats.stage_count, 10)
        self.assertGreater(stats.decisions_requiring_designation_check, 25)
        self.assertGreaterEqual(stats.referenced_source_count, 20)
        self.assertIn("derived simulation value", self.registry.matrix_scale)

    def test_all_matrices_are_bounded_and_immutable(self):
        for decision in self.registry.decisions:
            self.assertTrue(decision.options)
            for option in decision.options:
                for axis, value in option.matrix.items():
                    self.assertIn(axis, self.registry.axes)
                    self.assertGreaterEqual(value, -1.0)
                    self.assertLessEqual(value, 1.0)
                with self.assertRaises(TypeError):
                    option.matrix["invented"] = 1.0  # type: ignore[index]

    def test_all_source_references_resolve(self):
        for decision in self.registry.decisions:
            for source_ref in decision.source_refs:
                source = self.registry.source(source_ref)
                self.assertIsNotNone(source)
                assert source is not None
                self.assertTrue(source.url.startswith(("https://", "http://")))

    def test_oiv_recognition_does_not_authorize_gi_practice(self):
        decision = self.registry.decision("carbonic-mode")
        self.assertIsNotNone(decision)
        assert decision is not None
        self.assertIn("oiv-carbonic-maceration", decision.source_refs)
        self.assertTrue(decision.requires_designation_check)

        unresolved = self.registry.assess_authority("carbonic-mode")
        self.assertIsNone(unresolved.allowed)
        self.assertEqual(unresolved.status, "requires_external_legal_confirmation")
        self.assertFalse(unresolved.source_authority_is_sufficient)

        allowed = self.registry.assess_authority(
            "carbonic-mode", legal_confirmation=True
        )
        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.status, "confirmed_by_external_legal_layer")
        self.assertFalse(allowed.source_authority_is_sufficient)

        prohibited = self.registry.assess_authority(
            "carbonic-mode", legal_confirmation=False
        )
        self.assertFalse(prohibited.allowed)
        self.assertEqual(prohibited.status, "prohibited_by_external_legal_layer")

    def test_process_available_decision_is_not_promoted_to_gi_law(self):
        decision = self.registry.decision("harvest-sorting")
        self.assertIsNotNone(decision)
        assert decision is not None
        self.assertFalse(decision.requires_designation_check)
        assessment = self.registry.assess_authority("harvest-sorting")
        self.assertTrue(assessment.allowed)
        self.assertFalse(assessment.source_authority_is_sufficient)
        self.assertIn("not a claim", assessment.explanation.lower())

    def test_tokaj_special_process_keeps_product_scope_and_fails_closed(self):
        decision = self.registry.decision("tokaj-special-extraction")
        self.assertIsNotNone(decision)
        assert decision is not None
        self.assertTrue(decision.requires_designation_check)
        self.assertTrue(any("tokaj" in scope.lower() for scope in decision.authority_scopes))
        self.assertEqual(
            self.registry.assess_authority(decision.id).status,
            "requires_external_legal_confirmation",
        )
        self.assertIsNotNone(decision.option("eszencia-free-run"))

    def test_jerez_process_keeps_official_product_spec_scope(self):
        decision = self.registry.decision("jerez-cabeceo-sweetening")
        self.assertIsNotNone(decision)
        assert decision is not None
        source = self.registry.source("es-jerez-spec-2024-consolidated")
        self.assertIsNotNone(source)
        assert source is not None
        self.assertIn("jerez", source.jurisdiction.lower())
        self.assertIn("product-specification", source.kind)
        self.assertIsNone(self.registry.assess_authority(decision.id).allowed)

    def test_chemistry_sources_are_reused_not_duplicated(self):
        decision = self.registry.decision("fermentation-nutrient-timing")
        self.assertIsNotNone(decision)
        assert decision is not None
        source = self.registry.source("awri-yan-2026")
        self.assertIsNotNone(source)
        assert source is not None
        self.assertEqual(source.source_family, "process_chemistry_evidence")

    def test_option_lookup_does_not_silently_accept_unknown_choice(self):
        with self.assertRaises(WinemakingDecisionError):
            self.registry.option_matrix("mlf", "invented")
        with self.assertRaises(WinemakingDecisionError):
            self.registry.option_matrix("invented", "none")

    def test_high_level_matrix_value_stays_a_simulation_prior(self):
        matrix = self.registry.option_matrix("oak-new-percentage", "high")
        self.assertEqual(matrix["oakInfluence"], 0.45)
        self.assertEqual(matrix["fruitIntensity"], -0.05)
        decision = self.registry.decision("oak-new-percentage")
        assert decision is not None
        self.assertEqual(decision.source_refs, ())
        self.assertTrue(decision.requires_designation_check)


if __name__ == "__main__":
    unittest.main()
