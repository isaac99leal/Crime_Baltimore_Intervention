from __future__ import annotations

import unittest

from sommelier_v2.knowledge.decision_runtime import (
    DecisionRuntimeError,
    DecisionRuntimeInputs,
    apply_winemaking_decisions,
)
from sommelier_v2.knowledge.fermentation_process import FermentationPlan, MustComposition
from sommelier_v2.knowledge.maturation_process import (
    MaturationConstraintError,
    MaturationInput,
    simulate_maturation,
)


class MaturationDecisionRuntimeTests(unittest.TestCase):
    @staticmethod
    def must() -> MustComposition:
        return MustComposition(
            volume_l=1000.0,
            sugar_g_l=220.0,
            yan_mg_l=180.0,
            ph=3.45,
            titratable_acidity_g_l=6.0,
            malic_acid_g_l=2.4,
        )

    def apply(self, selections, *, inputs=DecisionRuntimeInputs(), **kwargs):
        return apply_winemaking_decisions(
            selections,
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            runtime_inputs=inputs,
            **kwargs,
        )

    def test_maturation_duration_label_does_not_create_days(self):
        result = self.apply({"maturation-duration": "long"})
        self.assertEqual(result.applications[0].status, "requires_measurement")
        self.assertEqual(result.maturation_plan.duration_days, 0.0)

        explicit = self.apply(
            {"maturation-duration": "long"},
            inputs=DecisionRuntimeInputs(maturation_duration_days=540.0),
        )
        self.assertEqual(explicit.applications[0].status, "applied")
        self.assertEqual(explicit.maturation_plan.duration_days, 540.0)

    def test_vessel_label_never_infers_oxygen_transfer(self):
        result = self.apply(
            {"maturation-vessel": "small-oak"},
            inputs=DecisionRuntimeInputs(maturation_duration_days=180.0),
        )
        self.assertEqual(result.maturation_plan.vessel_label, "small-oak")
        self.assertIsNone(result.maturation_plan.vessel_oxygen_transfer_mg_l_month)
        self.assertEqual(result.applications[0].status, "requires_measurement")

        explicit = self.apply(
            {"maturation-vessel": "small-oak"},
            inputs=DecisionRuntimeInputs(
                maturation_duration_days=180.0,
                vessel_oxygen_transfer_mg_l_month=0.65,
            ),
        )
        self.assertAlmostEqual(
            explicit.maturation_plan.vessel_oxygen_transfer_mg_l_month or 0.0,
            0.65,
        )
        self.assertEqual(explicit.applications[0].status, "applied")

    def test_no_lees_contact_has_exact_zero_endpoint(self):
        result = self.apply(
            {"lees-contact": "none"},
            inputs=DecisionRuntimeInputs(maturation_duration_days=180.0),
        )
        self.assertEqual(result.maturation_plan.lees_contact_until_day, 0.0)
        self.assertEqual(result.applications[0].status, "applied")

    def test_extended_lees_contact_requires_explicit_endpoint(self):
        unresolved = self.apply(
            {"lees-contact": "extended"},
            inputs=DecisionRuntimeInputs(maturation_duration_days=180.0),
        )
        self.assertEqual(unresolved.applications[0].status, "requires_measurement")
        self.assertIsNone(unresolved.maturation_plan.lees_contact_until_day)

        explicit = self.apply(
            {"lees-contact": "extended"},
            inputs=DecisionRuntimeInputs(
                maturation_duration_days=180.0,
                lees_contact_until_day=150.0,
            ),
        )
        self.assertEqual(explicit.maturation_plan.lees_contact_until_day, 150.0)
        self.assertEqual(explicit.applications[0].status, "applied")

    def test_batonnage_frequency_is_not_inferred_from_label(self):
        unresolved = self.apply(
            {"batonnage": "frequent"},
            inputs=DecisionRuntimeInputs(
                maturation_duration_days=120.0,
                lees_contact_until_day=120.0,
            ),
        )
        self.assertEqual(unresolved.applications[0].status, "requires_measurement")
        self.assertEqual(unresolved.maturation_plan.batonnage_events, ())

        explicit = self.apply(
            {"batonnage": "frequent"},
            inputs=DecisionRuntimeInputs(
                maturation_duration_days=120.0,
                lees_contact_until_day=120.0,
                batonnage_events=((10.0, 0.5), (20.0, 0.7), (35.0, 0.6)),
            ),
        )
        self.assertEqual(len(explicit.maturation_plan.batonnage_events), 3)
        self.assertEqual(explicit.applications[0].status, "applied")

    def test_oak_new_percentage_category_requires_exact_fraction(self):
        unresolved = self.apply(
            {"oak-new-percentage": "medium"},
            inputs=DecisionRuntimeInputs(maturation_duration_days=365.0),
        )
        self.assertEqual(unresolved.applications[0].status, "requires_measurement")

        explicit = self.apply(
            {"oak-new-percentage": "medium"},
            inputs=DecisionRuntimeInputs(
                maturation_duration_days=365.0,
                oak_contact_fraction=0.45,
            ),
        )
        self.assertAlmostEqual(explicit.maturation_plan.oak_contact_fraction, 0.45)
        self.assertEqual(explicit.applications[0].status, "applied")

        with self.assertRaises(DecisionRuntimeError):
            self.apply(
                {"oak-new-percentage": "medium"},
                inputs=DecisionRuntimeInputs(
                    maturation_duration_days=365.0,
                    oak_contact_fraction=0.80,
                ),
            )

    def test_zero_new_oak_is_exact_and_needs_no_midpoint(self):
        result = self.apply(
            {"oak-new-percentage": "zero"},
            inputs=DecisionRuntimeInputs(maturation_duration_days=365.0),
        )
        self.assertEqual(result.maturation_plan.oak_contact_fraction, 0.0)
        self.assertEqual(result.applications[0].status, "applied")

    def test_oak_context_is_retained_without_inventing_extraction_strength(self):
        result = self.apply(
            {
                "oak-species": "european",
                "oak-toast": "heavy",
                "oak-age": "new",
            },
            inputs=DecisionRuntimeInputs(maturation_duration_days=365.0),
        )
        self.assertEqual(result.maturation_plan.oak_extraction_prior, 0.0)
        self.assertEqual(
            result.maturation_plan.oak_context_labels,
            ("oak-species:european", "oak-toast:heavy", "oak-age:new"),
        )
        self.assertTrue(all(item.status == "requires_measurement" for item in result.applications))

        explicit = self.apply(
            {
                "oak-species": "european",
                "oak-toast": "heavy",
                "oak-age": "new",
            },
            inputs=DecisionRuntimeInputs(
                maturation_duration_days=365.0,
                oak_extraction_prior=0.72,
            ),
        )
        self.assertAlmostEqual(explicit.maturation_plan.oak_extraction_prior, 0.72)
        self.assertTrue(all(item.status == "applied" for item in explicit.applications))

    def test_topped_strategy_requires_physical_ullage_inputs_and_events(self):
        unresolved = self.apply(
            {"topping-ullage": "topped"},
            inputs=DecisionRuntimeInputs(maturation_duration_days=180.0),
        )
        self.assertEqual(unresolved.applications[0].status, "requires_measurement")

        still_missing_events = self.apply(
            {"topping-ullage": "topped"},
            inputs=DecisionRuntimeInputs(
                maturation_duration_days=180.0,
                headspace_oxygen_exposure_mg_l_month=0.25,
                evaporation_fraction_per_month=0.01,
            ),
        )
        self.assertEqual(still_missing_events.applications[0].status, "requires_measurement")

        explicit = self.apply(
            {"topping-ullage": "topped"},
            inputs=DecisionRuntimeInputs(
                maturation_duration_days=180.0,
                headspace_oxygen_exposure_mg_l_month=0.25,
                evaporation_fraction_per_month=0.01,
                topping_events=((30.0, 0.9), (60.0, 0.9), (90.0, 0.9)),
            ),
        )
        self.assertEqual(explicit.applications[0].status, "applied")
        self.assertEqual(len(explicit.maturation_plan.topping_events), 3)

    def test_microoxygenation_label_never_generates_oxygen_dose(self):
        unresolved = self.apply(
            {"micro-oxygenation": "low"},
            inputs=DecisionRuntimeInputs(maturation_duration_days=90.0),
        )
        self.assertEqual(unresolved.applications[0].status, "requires_measurement")
        self.assertEqual(unresolved.maturation_plan.oxygen_additions, ())

        explicit = self.apply(
            {"micro-oxygenation": "low"},
            inputs=DecisionRuntimeInputs(
                maturation_duration_days=90.0,
                microoxygenation_additions=((15.0, 0.20), (30.0, 0.20)),
            ),
        )
        self.assertEqual(explicit.applications[0].status, "applied")
        self.assertEqual(len(explicit.maturation_plan.oxygen_additions), 2)
        self.assertAlmostEqual(explicit.maturation_plan.oxygen_additions[0].oxygen_mg_l, 0.20)

    def test_runtime_built_plan_executes_end_to_end(self):
        runtime = self.apply(
            {
                "maturation-duration": "long",
                "maturation-vessel": "small-oak",
                "lees-contact": "extended",
                "batonnage": "occasional",
                "oak-new-percentage": "medium",
                "oak-species": "european",
                "topping-ullage": "topped",
                "micro-oxygenation": "low",
            },
            inputs=DecisionRuntimeInputs(
                maturation_duration_days=180.0,
                vessel_oxygen_transfer_mg_l_month=0.55,
                headspace_oxygen_exposure_mg_l_month=0.20,
                evaporation_fraction_per_month=0.01,
                oak_contact_fraction=0.40,
                oak_extraction_prior=0.60,
                lees_contact_until_day=150.0,
                batonnage_events=((30.0, 0.4), (60.0, 0.4)),
                topping_events=((45.0, 0.9), (90.0, 0.9), (135.0, 0.9)),
                microoxygenation_additions=((20.0, 0.15), (50.0, 0.15)),
            ),
        )
        self.assertFalse(runtime.unresolved)
        matured = simulate_maturation(
            MaturationInput(
                ph=3.45,
                free_so2_mg_l=32.0,
                tannin_index=0.55,
                phenolic_index=0.50,
                anthocyanin_index=0.45,
                microbial_risk=0.10,
                dissolved_oxygen_mg_l=0.35,
            ),
            runtime.maturation_plan,
        )
        self.assertTrue(matured.oxygen_model_complete)
        self.assertEqual(matured.batonnage_event_count, 2)
        self.assertEqual(matured.topping_event_count, 3)
        self.assertEqual(matured.oxygen_addition_count, 2)
        self.assertGreater(matured.final_state.oak_compound_index, 0.0)
        self.assertGreater(matured.final_state.lees_autolysis_index, 0.0)

    def test_final_plan_validation_catches_event_outside_duration(self):
        with self.assertRaises(MaturationConstraintError):
            self.apply(
                {"batonnage": "occasional"},
                inputs=DecisionRuntimeInputs(
                    maturation_duration_days=30.0,
                    batonnage_events=((45.0, 0.5),),
                ),
            )

    def test_protected_origin_still_requires_option_level_legal_confirmation(self):
        with self.assertRaises(DecisionRuntimeError):
            self.apply(
                {"maturation-vessel": "small-oak"},
                inputs=DecisionRuntimeInputs(
                    maturation_duration_days=180.0,
                    vessel_oxygen_transfer_mg_l_month=0.50,
                ),
                protected_designation=True,
            )

        allowed = self.apply(
            {"maturation-vessel": "small-oak"},
            inputs=DecisionRuntimeInputs(
                maturation_duration_days=180.0,
                vessel_oxygen_transfer_mg_l_month=0.50,
            ),
            protected_designation=True,
            legal_confirmations={"maturation-vessel:small-oak": True},
        )
        self.assertEqual(allowed.applications[0].status, "applied")


if __name__ == "__main__":
    unittest.main()
