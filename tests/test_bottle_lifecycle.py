from __future__ import annotations

import unittest

from sommelier_v2.knowledge.bottle_lifecycle import (
    BottleAgingPlan,
    BottleLifecycleConstraintError,
    age_cellar_wine,
)
from sommelier_v2.knowledge.cellar_pipeline import CellarHandoffInputs, run_cellar_pipeline
from sommelier_v2.knowledge.fermentation_process import FermentationPlan, MustComposition
from sommelier_v2.knowledge.packaging import PackagingPlan
from sommelier_v2.knowledge.schema import AgingArchetype


class BottleLifecycleTests(unittest.TestCase):
    @staticmethod
    def archetype() -> AgingArchetype:
        return AgingArchetype(
            id="test",
            name="Test",
            maturity_years=4.0,
            peak_years=8.0,
            decline_half_life_years=8.0,
            primary_half_life_years=6.0,
            floral_half_life_years=4.0,
            tertiary_onset_years=4.0,
            tertiary_peak_years=10.0,
            tannin_softening_half_life_years=8.0,
            freshness_half_life_years=7.0,
            oxidation_onset_years=10.0,
            oxidation_rate=0.2,
            complexity_peak_years=9.0,
            sediment_onset_years=7.0,
            color_shift_rate=0.08,
        )

    @staticmethod
    def cellar(*, do=None, closure=None, tartrate="unknown"):
        must = MustComposition(
            volume_l=500.0,
            sugar_g_l=12.0,
            yan_mg_l=240.0,
            ph=3.4,
            titratable_acidity_g_l=6.0,
            malic_acid_g_l=0.1,
            temp_c=24.0,
            free_so2_mg_l=0.0,
        )
        return run_cellar_pipeline(
            must=must,
            fermentation_plan=FermentationPlan(
                max_hours=240.0,
                post_fermentation_free_so2_mg_l=30.0,
            ),
            packaging_plan=PackagingPlan(
                prebottling_dissolved_oxygen_mg_l=do,
                closure_oxygen_exposure_prior=closure,
                tartrate_test_status=tartrate,
            ),
            handoff=CellarHandoffInputs(),
        )

    def test_strict_mode_rejects_incomplete_packaging_oxygen(self):
        with self.assertRaises(BottleLifecycleConstraintError):
            age_cellar_wine(
                self.archetype(),
                self.cellar(do=0.4, closure=None),
                BottleAgingPlan(age_years=5.0),
            )

    def test_explicit_conditional_mode_allows_incomplete_oxygen_with_warning(self):
        result = age_cellar_wine(
            self.archetype(),
            self.cellar(do=0.4, closure=None),
            BottleAgingPlan(age_years=5.0, require_complete_packaging_oxygen=False),
        )
        self.assertTrue(result.conditional_on_incomplete_oxygen)
        self.assertTrue(any("conditional" in warning for warning in result.warnings))

    def test_complete_packaging_oxygen_runs_without_conditional_flag(self):
        result = age_cellar_wine(
            self.archetype(),
            self.cellar(do=0.25, closure=0.2),
            BottleAgingPlan(age_years=5.0),
        )
        self.assertTrue(result.packaging_oxygen_complete)
        self.assertFalse(result.conditional_on_incomplete_oxygen)

    def test_higher_packaging_oxygen_accelerates_ageing(self):
        low = age_cellar_wine(
            self.archetype(),
            self.cellar(do=0.1, closure=0.05),
            BottleAgingPlan(age_years=8.0),
        )
        high = age_cellar_wine(
            self.archetype(),
            self.cellar(do=4.0, closure=0.9),
            BottleAgingPlan(age_years=8.0),
        )
        self.assertLess(high.state.primary_fruit, low.state.primary_fruit)
        self.assertGreater(high.state.color_evolution, low.state.color_evolution)

    def test_larger_bottle_modifier_slows_development(self):
        cellar = self.cellar(do=0.2, closure=0.1)
        standard = age_cellar_wine(
            self.archetype(), cellar, BottleAgingPlan(age_years=10.0, bottle_size_modifier=1.0)
        )
        larger = age_cellar_wine(
            self.archetype(), cellar, BottleAgingPlan(age_years=10.0, bottle_size_modifier=1.5)
        )
        self.assertGreater(larger.state.primary_fruit, standard.state.primary_fruit)

    def test_harsher_storage_modifier_accelerates_development(self):
        cellar = self.cellar(do=0.2, closure=0.1)
        normal = age_cellar_wine(
            self.archetype(), cellar, BottleAgingPlan(age_years=10.0, storage_modifier=1.0)
        )
        harsh = age_cellar_wine(
            self.archetype(), cellar, BottleAgingPlan(age_years=10.0, storage_modifier=1.7)
        )
        self.assertLess(harsh.state.primary_fruit, normal.state.primary_fruit)

    def test_tartrate_instability_remains_visible_in_bottle_result(self):
        result = age_cellar_wine(
            self.archetype(),
            self.cellar(do=0.2, closure=0.1, tartrate="tested_unstable"),
            BottleAgingPlan(age_years=2.0),
        )
        self.assertTrue(any("tartrate-unstable" in warning for warning in result.warnings))

    def test_plan_bounds_are_enforced(self):
        with self.assertRaises(BottleLifecycleConstraintError):
            BottleAgingPlan(age_years=-1.0)
        with self.assertRaises(BottleLifecycleConstraintError):
            BottleAgingPlan(age_years=5.0, bottle_size_modifier=0.0)


if __name__ == "__main__":
    unittest.main()
