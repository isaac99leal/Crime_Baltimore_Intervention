from __future__ import annotations

import unittest

from sommelier_v2.knowledge.fermentation_chemistry import (
    molecular_so2_mg_l,
    nutrient_timing_effect,
    white_juice_solids_risk,
)
from sommelier_v2.knowledge.fermentation_process import (
    FermentationPlan,
    MustComposition,
    NutrientAddition,
    run_fermentation,
)


class FermentationProcessChemistryTests(unittest.TestCase):
    @staticmethod
    def must(**changes) -> MustComposition:
        values = dict(
            volume_l=1000.0,
            sugar_g_l=220.0,
            yan_mg_l=220.0,
            ph=3.45,
            titratable_acidity_g_l=6.2,
            malic_acid_g_l=2.4,
            temp_c=24.0,
            free_so2_mg_l=5.0,
        )
        values.update(changes)
        return MustComposition(**values)

    def test_molecular_so2_falls_as_ph_rises(self):
        low_ph = molecular_so2_mg_l(30.0, 3.20)
        high_ph = molecular_so2_mg_l(30.0, 3.90)
        self.assertGreater(low_ph, high_ph)
        self.assertGreater(low_ph / high_ph, 4.0)

    def test_white_juice_turbidity_curve_is_non_monotonic(self):
        around_reference = white_juice_solids_risk("white", 100.0, 2.0)
        very_clear = white_juice_solids_risk("white", 15.0, 2.0)
        very_turbid = white_juice_solids_risk("white", 350.0, 2.0)
        self.assertLess(around_reference, very_clear)
        self.assertLess(around_reference, very_turbid)
        self.assertEqual(white_juice_solids_risk("red", 350.0, 12.0), 0.0)

    def test_late_dap_has_more_residual_nitrogen_risk_than_early_dap(self):
        early = nutrient_timing_effect(
            kind="dap",
            yan_mg_l=80.0,
            ethanol_pct=1.0,
            sugar_g_l=210.0,
            initial_sugar_g_l=220.0,
        )
        late = nutrient_timing_effect(
            kind="dap",
            yan_mg_l=80.0,
            ethanol_pct=10.5,
            sugar_g_l=55.0,
            initial_sugar_g_l=220.0,
        )
        self.assertGreater(late.residual_nitrogen_risk, early.residual_nitrogen_risk)
        self.assertLess(late.h2s_relief_index, early.h2s_relief_index)
        self.assertIsNotNone(late.warning)

    def test_compromised_must_changes_actual_va_kinetics(self):
        clean = run_fermentation(
            self.must(source_microbiological_risk=0.0),
            FermentationPlan(max_hours=1200.0),
        )
        compromised = run_fermentation(
            self.must(source_microbiological_risk=0.90),
            FermentationPlan(max_hours=1200.0),
        )
        self.assertGreater(
            compromised.final_volatile_acidity_g_l,
            clean.final_volatile_acidity_g_l,
        )
        self.assertGreater(
            compromised.initial_microbiological_risk,
            clean.initial_microbiological_risk,
        )

    def test_post_fermentation_so2_protection_is_ph_dependent(self):
        protected_low_ph = run_fermentation(
            self.must(ph=3.20),
            FermentationPlan(
                max_hours=1200.0,
                post_fermentation_free_so2_mg_l=30.0,
                post_fermentation_so2_delay_days=1.0,
            ),
        )
        same_free_so2_high_ph = run_fermentation(
            self.must(ph=3.90),
            FermentationPlan(
                max_hours=1200.0,
                post_fermentation_free_so2_mg_l=30.0,
                post_fermentation_so2_delay_days=1.0,
            ),
        )
        self.assertIsNotNone(protected_low_ph.molecular_so2_mg_l)
        self.assertIsNotNone(same_free_so2_high_ph.molecular_so2_mg_l)
        self.assertGreater(
            protected_low_ph.molecular_so2_mg_l or 0.0,
            same_free_so2_high_ph.molecular_so2_mg_l or 0.0,
        )
        self.assertLess(
            protected_low_ph.post_fermentation_microbiological_risk,
            same_free_so2_high_ph.post_fermentation_microbiological_risk,
        )

    def test_delayed_unprotected_wine_is_riskier_than_prompt_protection(self):
        protected = run_fermentation(
            self.must(ph=3.65, source_microbiological_risk=0.35),
            FermentationPlan(
                max_hours=1200.0,
                post_fermentation_free_so2_mg_l=35.0,
                post_fermentation_so2_delay_days=1.0,
            ),
        )
        delayed = run_fermentation(
            self.must(ph=3.65, source_microbiological_risk=0.35),
            FermentationPlan(
                max_hours=1200.0,
                post_fermentation_free_so2_mg_l=None,
                post_fermentation_so2_delay_days=30.0,
            ),
        )
        self.assertLess(
            protected.post_fermentation_microbiological_risk,
            delayed.post_fermentation_microbiological_risk,
        )
        self.assertTrue(any("post-fermentation" in warning.lower() for warning in delayed.warnings))

    def test_measured_white_turbidity_propagates_to_process_risk(self):
        reference = run_fermentation(
            self.must(juice_turbidity_ntu=100.0, solids_pct=2.0),
            FermentationPlan(style="white", max_hours=1200.0),
        )
        turbid = run_fermentation(
            self.must(juice_turbidity_ntu=350.0, solids_pct=2.0),
            FermentationPlan(style="white", max_hours=1200.0),
        )
        self.assertLess(reference.juice_solids_risk, turbid.juice_solids_risk)
        self.assertGreaterEqual(turbid.peak_h2s_risk, reference.peak_h2s_risk)

    def test_nutrient_kind_is_validated_and_default_remains_compatible(self):
        result = run_fermentation(
            self.must(),
            FermentationPlan(
                max_hours=1200.0,
                nutrient_additions=(NutrientAddition(hour=24.0, yan_mg_l=20.0),),
            ),
        )
        self.assertTrue(result.alcoholic_completed)


if __name__ == "__main__":
    unittest.main()
