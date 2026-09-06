from __future__ import annotations

import unittest

from sommelier_v2.knowledge.legal_practice_bridge import LegalPracticeBridge
from sommelier_v2.knowledge.legal_specs import LegalWineSpec
from sommelier_v2.knowledge.winemaking_decisions import WinemakingDecisionError


class LegalPracticeBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = LegalPracticeBridge()

    @staticmethod
    def spec(**overrides) -> LegalWineSpec:
        values = {
            "id": "test-spec",
            "country": "Testland",
            "appellation": "Test PDO",
            "source_ids": ("source-a",),
        }
        values.update(overrides)
        return LegalWineSpec(**values)

    def test_manual_harvest_requirement_confirms_hand_and_rejects_machine(self):
        spec = self.spec(manual_harvest_required=True)

        hand = self.bridge.assess_option(spec, "harvest-method", "hand")
        self.assertTrue(hand.legal_confirmation)
        self.assertIn("manual_harvest_requirement", hand.status)

        machine = self.bridge.assess_option(spec, "harvest-method", "machine")
        self.assertFalse(machine.legal_confirmation)
        self.assertIn("prohibited", machine.status)

    def test_absence_of_manual_harvest_requirement_does_not_authorize_machine(self):
        spec = self.spec(manual_harvest_required=False)
        machine = self.bridge.assess_option(spec, "harvest-method", "machine")
        self.assertIsNone(machine.legal_confirmation)
        self.assertIn("does not prove", machine.reason)

        authority = self.bridge.authority_assessment(spec, "harvest-method", "machine")
        self.assertIsNone(authority.allowed)
        self.assertEqual(authority.status, "requires_external_legal_confirmation")

    def test_explicit_traditional_method_confirms_only_traditional_option(self):
        spec = self.spec(required_method="traditional method")

        traditional = self.bridge.assess_option(spec, "sparkling-secondary", "traditional")
        self.assertTrue(traditional.legal_confirmation)

        tank = self.bridge.assess_option(spec, "sparkling-secondary", "tank")
        self.assertFalse(tank.legal_confirmation)

        none = self.bridge.assess_option(spec, "sparkling-secondary", "none")
        self.assertFalse(none.legal_confirmation)

    def test_known_method_alias_is_normalized(self):
        spec = self.spec(required_method="Méthode traditionnelle")
        result = self.bridge.assess_option(spec, "sparkling-secondary", "traditional")
        self.assertTrue(result.legal_confirmation)

    def test_unknown_required_method_does_not_generate_false_prohibition(self):
        spec = self.spec(required_method="some separately reviewed method not mapped here")
        for option_id in ("traditional", "tank", "ancestral", "none"):
            result = self.bridge.assess_option(spec, "sparkling-secondary", option_id)
            self.assertIsNone(result.legal_confirmation)

    def test_unstructured_cellar_practice_remains_unresolved(self):
        spec = self.spec(manual_harvest_required=True, required_method="traditional method")
        result = self.bridge.assess_option(spec, "maturation-vessel", "small-oak")
        self.assertIsNone(result.legal_confirmation)
        self.assertEqual(result.status, "legal_practice_rule_not_structured")

        authority = self.bridge.authority_assessment(spec, "maturation-vessel", "small-oak")
        self.assertIsNone(authority.allowed)

    def test_no_designation_gate_is_not_promoted_to_legal_permission(self):
        spec = self.spec()
        practice = self.bridge.assess_option(spec, "harvest-sorting", "strict")
        self.assertIsNone(practice.legal_confirmation)
        self.assertEqual(practice.status, "no_designation_gate_in_decision_matrix")

        authority = self.bridge.authority_assessment(spec, "harvest-sorting", "strict")
        self.assertTrue(authority.allowed)
        self.assertEqual(authority.status, "process_available_no_matrix_designation_gate")
        self.assertFalse(authority.source_authority_is_sufficient)

    def test_source_ids_are_carried_as_evidence_without_becoming_authority(self):
        spec = self.spec(source_ids=("official-spec-a", "official-spec-b"))
        result = self.bridge.assess_option(spec, "maturation-vessel", "small-oak")
        self.assertEqual(result.evidence_source_ids, ("official-spec-a", "official-spec-b"))
        self.assertIsNone(result.legal_confirmation)

    def test_invalid_option_fails_instead_of_silently_falling_back(self):
        with self.assertRaises(WinemakingDecisionError):
            self.bridge.assess_option(self.spec(), "harvest-method", "teleport")


if __name__ == "__main__":
    unittest.main()
