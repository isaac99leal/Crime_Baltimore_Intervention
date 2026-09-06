from __future__ import annotations

import unittest
from datetime import date

from sommelier_v2.knowledge.cellar_pipeline import (
    CellarHandoffInputs,
    CellarPipelinePlan,
    run_cellar_pipeline,
)
from sommelier_v2.knowledge.fermentation_process import FermentationPlan, MustComposition
from sommelier_v2.knowledge.legal_specs import LegalWineSpec
from sommelier_v2.knowledge.maturation_process import MaturationPlan
from sommelier_v2.knowledge.release_runtime import (
    ReleaseRuntimeConstraintError,
    ReleaseRuntimeInputs,
    validate_cellar_release,
)


class ReleaseRuntimeTests(unittest.TestCase):
    @staticmethod
    def must() -> MustComposition:
        return MustComposition(
            volume_l=500.0,
            sugar_g_l=12.0,
            yan_mg_l=240.0,
            ph=3.4,
            titratable_acidity_g_l=6.0,
            malic_acid_g_l=0.10,
            temp_c=24.0,
            free_so2_mg_l=0.0,
        )

    @staticmethod
    def fermentation_plan() -> FermentationPlan:
        return FermentationPlan(
            max_hours=240.0,
            post_fermentation_free_so2_mg_l=28.0,
        )

    def pipeline(self, *, selections=None, maturation_days: float | None = None):
        if maturation_days is None:
            return run_cellar_pipeline(
                must=self.must(),
                fermentation_plan=self.fermentation_plan(),
                selections=selections,
            )
        return run_cellar_pipeline(
            must=self.must(),
            fermentation_plan=self.fermentation_plan(),
            selections=selections,
            maturation_plan=MaturationPlan(duration_days=maturation_days),
            pipeline_plan=CellarPipelinePlan(run_maturation=True),
            handoff=CellarHandoffInputs(
                maturation_tannin_index=0.1,
                maturation_phenolic_index=0.1,
                maturation_anthocyanin_index=0.05,
            ),
        )

    def test_actual_fermentation_values_feed_release_rules(self):
        spec = LegalWineSpec(
            id="test-release",
            country="Testland",
            appellation="Test PDO",
            min_final_alcohol_pct=0.5,
            max_residual_sugar_g_l=2.1,
            max_malic_acid_g_l=0.2,
            min_total_aging_months=12,
        )
        decision = validate_cellar_release(
            spec,
            self.pipeline(),
            ReleaseRuntimeInputs(total_aging_months=12),
        )
        self.assertTrue(decision.eligible, decision.issues)

    def test_manual_harvest_is_derived_only_from_explicit_selection(self):
        spec = LegalWineSpec(
            id="manual",
            country="Testland",
            appellation="Manual PDO",
            manual_harvest_required=True,
        )
        no_selection = validate_cellar_release(
            spec,
            self.pipeline(),
            ReleaseRuntimeInputs(total_aging_months=0),
        )
        self.assertFalse(no_selection.eligible)
        self.assertTrue(any("Manual harvest" in issue for issue in no_selection.issues))

        hand = validate_cellar_release(
            spec,
            self.pipeline(selections={"harvest-method": "hand"}),
            ReleaseRuntimeInputs(total_aging_months=0),
        )
        self.assertTrue(hand.eligible, hand.issues)

    def test_confirmed_sparkling_selection_can_use_exact_legal_method_vocabulary(self):
        spec = LegalWineSpec(
            id="traditional",
            country="Testland",
            appellation="Traditional PDO",
            required_method="traditional method",
        )
        pipeline = self.pipeline(selections={"sparkling-secondary": "traditional"})
        decision = validate_cellar_release(
            spec,
            pipeline,
            ReleaseRuntimeInputs(total_aging_months=0),
        )
        self.assertTrue(decision.eligible, decision.issues)

    def test_unmodeled_finished_analytics_remain_fail_closed(self):
        spec = LegalWineSpec(
            id="analytics",
            country="Testland",
            appellation="Analytical PDO",
            min_total_acidity_g_l=5.0,
            min_dry_extract_g_l=18.0,
            max_total_alcohol_pct=15.0,
        )
        missing = validate_cellar_release(
            spec,
            self.pipeline(),
            ReleaseRuntimeInputs(total_aging_months=0, require_complete=True),
        )
        self.assertFalse(missing.eligible)
        self.assertTrue(any("Total acidity" in issue for issue in missing.issues))
        self.assertTrue(any("Dry extract" in issue for issue in missing.issues))
        self.assertTrue(any("Total alcoholic strength" in issue for issue in missing.issues))

        measured = validate_cellar_release(
            spec,
            self.pipeline(),
            ReleaseRuntimeInputs(
                total_aging_months=0,
                total_acidity_g_l=6.2,
                dry_extract_g_l=22.0,
                total_alcohol_pct=1.0,
            ),
        )
        self.assertTrue(measured.eligible, measured.issues)

    def test_wood_aging_claim_cannot_exceed_executed_maturation_duration(self):
        spec = LegalWineSpec(id="wood", country="Testland", appellation="Wood PDO")
        decision = validate_cellar_release(
            spec,
            self.pipeline(maturation_days=30.0),
            ReleaseRuntimeInputs(total_aging_months=2, wood_aging_months=2),
        )
        self.assertFalse(decision.eligible)
        self.assertTrue(any("wood-aging" in issue for issue in decision.issues))

    def test_calendar_release_rules_use_explicit_dates(self):
        spec = LegalWineSpec(
            id="calendar",
            country="Testland",
            appellation="Calendar PDO",
            min_elevage_year_offset=1,
            min_elevage_until_month=3,
            min_elevage_until_day=1,
            release_year_offset=2,
            earliest_release_month=1,
            earliest_release_day=1,
        )
        early = validate_cellar_release(
            spec,
            self.pipeline(),
            ReleaseRuntimeInputs(
                total_aging_months=0,
                vintage_year=2024,
                elevage_end_date=date(2025, 2, 28),
                release_date=date(2025, 12, 31),
            ),
        )
        self.assertFalse(early.eligible)

        legal = validate_cellar_release(
            spec,
            self.pipeline(),
            ReleaseRuntimeInputs(
                total_aging_months=0,
                vintage_year=2024,
                elevage_end_date=date(2025, 3, 1),
                release_date=date(2026, 1, 1),
            ),
        )
        self.assertTrue(legal.eligible, legal.issues)

    def test_release_date_cannot_precede_elevage_end(self):
        with self.assertRaises(ReleaseRuntimeConstraintError):
            ReleaseRuntimeInputs(
                total_aging_months=12,
                elevage_end_date=date(2026, 3, 1),
                release_date=date(2026, 2, 1),
            )

    def test_wood_plus_bottle_cannot_exceed_total_aging(self):
        with self.assertRaises(ReleaseRuntimeConstraintError):
            ReleaseRuntimeInputs(
                total_aging_months=12,
                wood_aging_months=8,
                bottle_aging_months=6,
            )


if __name__ == "__main__":
    unittest.main()
