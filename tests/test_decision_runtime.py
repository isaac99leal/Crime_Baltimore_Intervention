from __future__ import annotations

import unittest

from sommelier_v2.knowledge.decision_runtime import (
    DecisionRuntimeError,
    DecisionRuntimeInputs,
    apply_winemaking_decisions,
)
from sommelier_v2.knowledge.fermentation_process import FermentationPlan, MustComposition
from sommelier_v2.knowledge.legal_specs import LegalWineSpec
from sommelier_v2.knowledge.packaging import PackagingPlan


class DecisionRuntimeTests(unittest.TestCase):
    @staticmethod
    def must() -> MustComposition:
        return MustComposition(
            volume_l=1000.0,
            sugar_g_l=220.0,
            yan_mg_l=180.0,
            ph=3.4,
            titratable_acidity_g_l=6.0,
            malic_acid_g_l=2.5,
        )

    def test_full_and_whole_cluster_map_to_exact_runtime_fraction(self):
        full = apply_winemaking_decisions(
            {"destemming": "full"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
        )
        self.assertEqual(full.fermentation_plan.alcoholic_params.whole_cluster_fraction, 0.0)

        whole = apply_winemaking_decisions(
            {"destemming": "whole-cluster"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
        )
        self.assertEqual(whole.fermentation_plan.alcoholic_params.whole_cluster_fraction, 1.0)

    def test_partial_whole_cluster_needs_explicit_fraction(self):
        unresolved = apply_winemaking_decisions(
            {"destemming": "partial"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
        )
        self.assertEqual(unresolved.applications[0].status, "requires_measurement")
        self.assertEqual(unresolved.fermentation_plan.alcoholic_params.whole_cluster_fraction, 0.0)

        applied = apply_winemaking_decisions(
            {"destemming": "partial"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            runtime_inputs=DecisionRuntimeInputs(partial_whole_cluster_fraction=0.42),
        )
        self.assertAlmostEqual(applied.fermentation_plan.alcoholic_params.whole_cluster_fraction, 0.42)

    def test_oxygen_management_uses_explicit_simulator_prior(self):
        protected = apply_winemaking_decisions(
            {"oxygen-fermentation": "protected"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
        )
        oxygenated = apply_winemaking_decisions(
            {"oxygen-fermentation": "oxygenated"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
        )
        self.assertLess(
            protected.fermentation_plan.alcoholic_params.oxygen_management_index,
            oxygenated.fermentation_plan.alcoholic_params.oxygen_management_index,
        )
        self.assertIn("derived simulator", protected.applications[0].note)

    def test_temperature_trajectory_requires_explicit_schedule(self):
        unresolved = apply_winemaking_decisions(
            {"fermentation-temperature-trajectory": "controlled-ramp"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
        )
        self.assertEqual(unresolved.applications[0].status, "requires_measurement")
        self.assertEqual(unresolved.fermentation_plan.alcoholic_params.temperature_schedule, ())

        schedule = ((0.0, 18.0), (72.0, 24.0), (144.0, 26.0))
        applied = apply_winemaking_decisions(
            {"fermentation-temperature-trajectory": "controlled-ramp"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            runtime_inputs=DecisionRuntimeInputs(fermentation_temperature_schedule=schedule),
        )
        self.assertEqual(applied.fermentation_plan.alcoholic_params.temperature_schedule, schedule)
        self.assertEqual(applied.applications[0].status, "applied")

    def test_mlf_blocked_complete_and_partial_targets(self):
        blocked = apply_winemaking_decisions(
            {"mlf": "blocked"},
            must=self.must(),
            fermentation_plan=FermentationPlan(malolactic=True),
        )
        self.assertFalse(blocked.fermentation_plan.malolactic)

        complete = apply_winemaking_decisions(
            {"mlf": "complete"},
            must=self.must(),
            fermentation_plan=FermentationPlan(malolactic=False),
        )
        self.assertTrue(complete.fermentation_plan.malolactic)
        self.assertAlmostEqual(complete.fermentation_plan.malolactic_params.target_malic_g_l, 0.10)

        unresolved = apply_winemaking_decisions(
            {"mlf": "partial"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
        )
        self.assertEqual(unresolved.applications[0].status, "requires_measurement")

        partial = apply_winemaking_decisions(
            {"mlf": "partial"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            runtime_inputs=DecisionRuntimeInputs(partial_mlf_target_malic_g_l=1.25),
        )
        self.assertTrue(partial.fermentation_plan.malolactic)
        self.assertAlmostEqual(partial.fermentation_plan.malolactic_params.target_malic_g_l, 1.25)
        self.assertEqual(partial.applications[0].status, "applied")

    def test_partial_mlf_rejects_nonpartial_target(self):
        with self.assertRaises(DecisionRuntimeError):
            apply_winemaking_decisions(
                {"mlf": "partial"},
                must=self.must(),
                fermentation_plan=FermentationPlan(),
                runtime_inputs=DecisionRuntimeInputs(partial_mlf_target_malic_g_l=0.10),
            )
        with self.assertRaises(DecisionRuntimeError):
            apply_winemaking_decisions(
                {"mlf": "partial"},
                must=self.must(),
                fermentation_plan=FermentationPlan(),
                runtime_inputs=DecisionRuntimeInputs(partial_mlf_target_malic_g_l=2.5),
            )

    def test_sterile_filtration_enables_sterile_packaging_credit(self):
        result = apply_winemaking_decisions(
            {"filtration": "sterile"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
        )
        self.assertTrue(result.fermentation_plan.sterile_packaging)

    def test_qualitative_bottling_oxygen_does_not_invent_measurement(self):
        result = apply_winemaking_decisions(
            {"bottling-oxygen": "very-low"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            packaging_plan=PackagingPlan(),
        )
        self.assertIsNone(result.packaging_plan.prebottling_dissolved_oxygen_mg_l)
        self.assertEqual(result.applications[0].status, "requires_measurement")

        measured = apply_winemaking_decisions(
            {"bottling-oxygen": "very-low"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            runtime_inputs=DecisionRuntimeInputs(prebottling_dissolved_oxygen_mg_l=0.35),
        )
        self.assertAlmostEqual(measured.packaging_plan.prebottling_dissolved_oxygen_mg_l or 0.0, 0.35)

    def test_closure_choice_does_not_infer_otr(self):
        result = apply_winemaking_decisions(
            {"closure": "very-low-otr"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
        )
        self.assertIsNone(result.packaging_plan.closure_oxygen_exposure_prior)
        self.assertEqual(result.applications[0].status, "requires_measurement")

    def test_measured_turbidity_is_applied_without_using_option_as_measurement(self):
        result = apply_winemaking_decisions(
            {"white-juice-turbidity": "moderate-around-100ntu"},
            must=self.must(),
            fermentation_plan=FermentationPlan(style="white"),
            runtime_inputs=DecisionRuntimeInputs(juice_turbidity_ntu=112.0),
        )
        self.assertEqual(result.must.juice_turbidity_ntu, 112.0)

    def test_protected_designation_fails_closed_without_option_confirmation(self):
        with self.assertRaises(DecisionRuntimeError):
            apply_winemaking_decisions(
                {"destemming": "full"},
                must=self.must(),
                fermentation_plan=FermentationPlan(),
                protected_designation=True,
            )

        allowed = apply_winemaking_decisions(
            {"destemming": "full"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            protected_designation=True,
            legal_confirmations={"destemming:full": True},
        )
        self.assertEqual(allowed.fermentation_plan.alcoholic_params.whole_cluster_fraction, 0.0)

    def test_reviewed_manual_harvest_rule_can_supply_confirmation(self):
        spec = LegalWineSpec(
            id="manual-spec",
            country="Testland",
            appellation="Manual PDO",
            manual_harvest_required=True,
            source_ids=("official-spec",),
        )
        result = apply_winemaking_decisions(
            {"harvest-method": "hand"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            protected_designation=True,
            legal_spec=spec,
        )
        self.assertEqual(result.applications[0].status, "matrix_only")

        with self.assertRaises(DecisionRuntimeError):
            apply_winemaking_decisions(
                {"harvest-method": "machine"},
                must=self.must(),
                fermentation_plan=FermentationPlan(),
                protected_designation=True,
                legal_spec=spec,
            )

    def test_axis_effects_are_bounded_when_multiple_priors_accumulate(self):
        result = apply_winemaking_decisions(
            {
                "fortification": "during-fermentation",
                "tokaj-special-extraction": "eszencia-free-run",
            },
            must=self.must(),
            fermentation_plan=FermentationPlan(),
        )
        self.assertLessEqual(result.axis_effects["sweetness"], 1.0)
        self.assertEqual(result.axis_effects["sweetness"], 1.0)

    def test_invalid_runtime_measurement_fails(self):
        with self.assertRaises(DecisionRuntimeError):
            apply_winemaking_decisions(
                {"closure": "moderate-otr"},
                must=self.must(),
                fermentation_plan=FermentationPlan(),
                runtime_inputs=DecisionRuntimeInputs(closure_oxygen_exposure_prior=1.2),
            )

    def test_invalid_temperature_schedule_fails(self):
        with self.assertRaises(DecisionRuntimeError):
            apply_winemaking_decisions(
                {"fermentation-temperature-trajectory": "controlled-ramp"},
                must=self.must(),
                fermentation_plan=FermentationPlan(),
                runtime_inputs=DecisionRuntimeInputs(
                    fermentation_temperature_schedule=((24.0, 20.0), (12.0, 22.0))
                ),
            )


if __name__ == "__main__":
    unittest.main()
