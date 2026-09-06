from __future__ import annotations

import unittest

from sommelier_v2.knowledge.maturation_process import (
    BatonnageEvent,
    MaturationConstraintError,
    MaturationInput,
    MaturationPlan,
    OxygenAddition,
    ToppingEvent,
    simulate_maturation,
)


class MaturationProcessTests(unittest.TestCase):
    @staticmethod
    def initial(**overrides) -> MaturationInput:
        values = {
            "ph": 3.45,
            "free_so2_mg_l": 30.0,
            "tannin_index": 0.55,
            "phenolic_index": 0.50,
            "anthocyanin_index": 0.45,
            "microbial_risk": 0.10,
            "dissolved_oxygen_mg_l": 0.40,
        }
        values.update(overrides)
        return MaturationInput(**values)

    def test_missing_oxygen_measurements_remain_unknown_not_zero(self):
        result = simulate_maturation(
            self.initial(dissolved_oxygen_mg_l=None),
            MaturationPlan(duration_days=90.0),
        )
        self.assertFalse(result.oxygen_model_complete)
        self.assertIsNone(result.final_state.dissolved_oxygen_mg_l)
        self.assertIsNone(result.final_state.cumulative_oxygen_input_mg_l)
        self.assertIsNone(result.final_state.oxidative_development)
        self.assertIsNone(result.final_state.reductive_risk)
        self.assertTrue(result.warnings)

    def test_explicit_oxygen_transfer_consumes_so2_and_moves_oxidative_state(self):
        result = simulate_maturation(
            self.initial(),
            MaturationPlan(
                duration_days=120.0,
                vessel_oxygen_transfer_mg_l_month=0.8,
                headspace_oxygen_exposure_mg_l_month=0.3,
                evaporation_fraction_per_month=0.01,
            ),
        )
        self.assertTrue(result.oxygen_model_complete)
        self.assertIsNotNone(result.final_state.cumulative_oxygen_input_mg_l)
        self.assertGreater(result.final_state.cumulative_oxygen_input_mg_l or 0.0, 0.0)
        self.assertLess(result.final_state.free_so2_mg_l, 30.0)
        self.assertGreater(result.final_state.oxidative_development or 0.0, 0.0)
        self.assertGreater(result.final_state.polymerized_tannin_index, 0.0)

    def test_topping_reduces_ullage_relative_to_untopped_wine(self):
        base_plan = dict(
            duration_days=180.0,
            vessel_oxygen_transfer_mg_l_month=0.5,
            headspace_oxygen_exposure_mg_l_month=0.5,
            evaporation_fraction_per_month=0.02,
        )
        untopped = simulate_maturation(self.initial(), MaturationPlan(**base_plan))
        topped = simulate_maturation(
            self.initial(),
            MaturationPlan(
                **base_plan,
                topping_events=(
                    ToppingEvent(60.0, 0.90),
                    ToppingEvent(120.0, 0.90),
                ),
            ),
        )
        self.assertEqual(topped.topping_event_count, 2)
        self.assertLess(topped.final_state.ullage_fraction, untopped.final_state.ullage_fraction)
        self.assertLess(
            topped.final_state.cumulative_oxygen_input_mg_l or 0.0,
            untopped.final_state.cumulative_oxygen_input_mg_l or 0.0,
        )

    def test_oak_name_cannot_create_extraction_without_numeric_prior(self):
        no_prior = simulate_maturation(
            self.initial(),
            MaturationPlan(
                duration_days=180.0,
                oak_contact_fraction=1.0,
                oak_extraction_prior=0.0,
                oak_context_labels=("new", "european", "heavy-toast"),
            ),
        )
        explicit = simulate_maturation(
            self.initial(),
            MaturationPlan(
                duration_days=180.0,
                oak_contact_fraction=0.60,
                oak_extraction_prior=0.75,
                oak_context_labels=("new", "european", "heavy-toast"),
            ),
        )
        self.assertEqual(no_prior.final_state.oak_compound_index, 0.0)
        self.assertGreater(explicit.final_state.oak_compound_index, 0.0)

    def test_lees_contact_and_batonnage_build_autolysis_index(self):
        lees_only = simulate_maturation(
            self.initial(),
            MaturationPlan(duration_days=120.0, lees_contact_until_day=120.0),
        )
        stirred = simulate_maturation(
            self.initial(),
            MaturationPlan(
                duration_days=120.0,
                lees_contact_until_day=120.0,
                batonnage_events=(
                    BatonnageEvent(15.0, 0.5),
                    BatonnageEvent(30.0, 0.5),
                    BatonnageEvent(45.0, 0.5),
                ),
            ),
        )
        self.assertEqual(stirred.batonnage_event_count, 3)
        self.assertGreater(
            stirred.final_state.lees_autolysis_index,
            lees_only.final_state.lees_autolysis_index,
        )

    def test_deliberate_oxygen_additions_are_explicit_and_counted(self):
        base = simulate_maturation(
            self.initial(),
            MaturationPlan(
                duration_days=60.0,
                vessel_oxygen_transfer_mg_l_month=0.2,
                headspace_oxygen_exposure_mg_l_month=0.1,
            ),
        )
        oxygenated = simulate_maturation(
            self.initial(),
            MaturationPlan(
                duration_days=60.0,
                vessel_oxygen_transfer_mg_l_month=0.2,
                headspace_oxygen_exposure_mg_l_month=0.1,
                oxygen_additions=(
                    OxygenAddition(10.0, 0.40),
                    OxygenAddition(30.0, 0.40),
                ),
            ),
        )
        self.assertEqual(oxygenated.oxygen_addition_count, 2)
        self.assertGreater(
            oxygenated.final_state.cumulative_oxygen_input_mg_l or 0.0,
            base.final_state.cumulative_oxygen_input_mg_l or 0.0,
        )
        self.assertGreater(
            oxygenated.final_state.oxidative_development or 0.0,
            base.final_state.oxidative_development or 0.0,
        )

    def test_low_so2_high_ph_has_higher_microbial_risk(self):
        protected = simulate_maturation(
            self.initial(ph=3.20, free_so2_mg_l=45.0),
            MaturationPlan(duration_days=180.0),
        )
        exposed = simulate_maturation(
            self.initial(ph=4.00, free_so2_mg_l=2.0),
            MaturationPlan(duration_days=180.0),
        )
        self.assertGreater(exposed.final_state.microbial_risk, protected.final_state.microbial_risk)

    def test_invalid_maturation_inputs_fail_closed(self):
        with self.assertRaises(MaturationConstraintError):
            MaturationPlan(duration_days=-1.0)
        with self.assertRaises(MaturationConstraintError):
            MaturationPlan(duration_days=100.0, lees_contact_until_day=120.0)
        with self.assertRaises(MaturationConstraintError):
            MaturationPlan(
                duration_days=100.0,
                topping_events=(ToppingEvent(110.0, 1.0),),
            )
        with self.assertRaises(MaturationConstraintError):
            OxygenAddition(day=1.0, oxygen_mg_l=25.0)


if __name__ == "__main__":
    unittest.main()
