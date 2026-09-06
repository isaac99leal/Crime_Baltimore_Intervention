from __future__ import annotations

import unittest

from sommelier_v2.knowledge.fermentation_engine import (
    AlcoholicFermentationParams,
    MalolacticParams,
    MalolacticState,
    initial_state,
    run_malolactic,
    step_alcoholic_fermentation,
    temperature_control_target,
)
from sommelier_v2.knowledge.fermentation_process import (
    FermentationPlan,
    MustComposition,
    run_fermentation,
)


class FermentationTrajectoryAndPartialMlfTests(unittest.TestCase):
    def test_temperature_schedule_interpolates_between_control_points(self):
        params = AlcoholicFermentationParams(
            temperature_schedule=((0.0, 18.0), (10.0, 28.0), (20.0, 24.0))
        )
        self.assertAlmostEqual(temperature_control_target(0.0, params) or 0.0, 18.0)
        self.assertAlmostEqual(temperature_control_target(5.0, params) or 0.0, 23.0)
        self.assertAlmostEqual(temperature_control_target(15.0, params) or 0.0, 26.0)
        self.assertAlmostEqual(temperature_control_target(30.0, params) or 0.0, 24.0)

    def test_active_temperature_schedule_can_heat_as_well_as_cool(self):
        state = initial_state(sugar_g_l=200.0, yan_mg_l=180.0, temp_c=18.0)
        base = AlcoholicFermentationParams(
            heat_c_per_g_l_sugar=0.0,
            ambient_exchange_per_h=0.0,
            cooling_setpoint_c=None,
        )
        controlled = AlcoholicFermentationParams(
            heat_c_per_g_l_sugar=0.0,
            ambient_exchange_per_h=0.0,
            cooling_setpoint_c=None,
            temperature_schedule=((0.0, 30.0),),
            temperature_control_strength_per_h=0.5,
        )
        base_next = step_alcoholic_fermentation(state, base, dt_hours=1.0)
        controlled_next = step_alcoholic_fermentation(state, controlled, dt_hours=1.0)
        self.assertAlmostEqual(base_next.temp_c, 18.0)
        self.assertAlmostEqual(controlled_next.temp_c, 24.0)

    def test_temperature_schedule_validation_fails_on_reversed_hours(self):
        with self.assertRaises(ValueError):
            AlcoholicFermentationParams(
                temperature_schedule=((12.0, 20.0), (6.0, 22.0))
            )

    def test_partial_mlf_hits_explicit_malic_target_exactly(self):
        state = MalolacticState(
            day=0.0,
            malic_g_l=3.0,
            lactic_g_l=0.0,
            ph=3.45,
            temp_c=20.0,
            ethanol_pct=12.0,
            free_so2_mg_l=0.0,
        )
        params = MalolacticParams(
            base_malic_rate_g_l_day=1.0,
            target_malic_g_l=1.5,
        )
        history = run_malolactic(state, params, max_days=30.0)
        self.assertTrue(history[-1].finished)
        self.assertAlmostEqual(history[-1].malic_g_l, 1.5, places=9)
        self.assertGreater(history[-1].lactic_g_l, 0.0)

    def test_default_mlf_target_preserves_complete_behavior(self):
        self.assertAlmostEqual(MalolacticParams().target_malic_g_l, 0.10)

    def test_process_orchestration_uses_partial_mlf_target(self):
        must = MustComposition(
            volume_l=500.0,
            sugar_g_l=40.0,
            yan_mg_l=250.0,
            ph=3.45,
            titratable_acidity_g_l=6.0,
            malic_acid_g_l=2.5,
            temp_c=24.0,
            free_so2_mg_l=0.0,
        )
        plan = FermentationPlan(
            malolactic=True,
            malolactic_params=MalolacticParams(
                base_malic_rate_g_l_day=1.0,
                target_malic_g_l=1.2,
            ),
            mlf_start_temp_c=20.0,
        )
        result = run_fermentation(must, plan)
        self.assertTrue(result.alcoholic_completed)
        self.assertTrue(result.malolactic_completed)
        self.assertAlmostEqual(result.final_malic_acid_g_l, 1.2, places=9)


if __name__ == "__main__":
    unittest.main()
