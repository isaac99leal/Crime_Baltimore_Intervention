from __future__ import annotations

import unittest

from sommelier_v2.knowledge.decision_runtime import (
    DecisionRuntimeInputs,
    apply_winemaking_decisions,
)
from sommelier_v2.knowledge.extraction_process import (
    CapManagementEvent,
    ExtractionConstraintError,
    ExtractionPlan,
    simulate_extraction,
)
from sommelier_v2.knowledge.fermentation_engine import FermentationState
from sommelier_v2.knowledge.fermentation_process import FermentationPlan, MustComposition


class ExtractionProcessTests(unittest.TestCase):
    @staticmethod
    def history() -> tuple[FermentationState, ...]:
        return (
            FermentationState(0.0, 220.0, 0.0, 180.0, 20.0, 0.20),
            FermentationState(24.0, 190.0, 1.8, 165.0, 24.0, 0.45),
            FermentationState(48.0, 150.0, 4.2, 145.0, 27.0, 0.70),
            FermentationState(72.0, 105.0, 6.9, 125.0, 28.0, 0.90),
            FermentationState(96.0, 60.0, 9.6, 105.0, 27.0, 1.05),
            FermentationState(120.0, 20.0, 12.0, 90.0, 25.0, 1.10),
        )

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

    def test_cap_management_events_increase_modeled_extraction(self):
        baseline = simulate_extraction(self.history(), ExtractionPlan())
        managed = simulate_extraction(
            self.history(),
            ExtractionPlan(
                cap_management_events=(
                    CapManagementEvent(24.0, 0.8, "punchdown"),
                    CapManagementEvent(48.0, 0.8, "punchdown"),
                    CapManagementEvent(72.0, 0.8, "punchdown"),
                )
            ),
        )
        self.assertEqual(managed.cap_event_count, 3)
        self.assertGreater(managed.anthocyanin_index, baseline.anthocyanin_index)
        self.assertGreater(managed.tannin_index, baseline.tannin_index)
        self.assertGreater(managed.phenolic_index, baseline.phenolic_index)

    def test_shorter_skin_contact_reduces_extraction_and_records_hours(self):
        short = simulate_extraction(
            self.history(),
            ExtractionPlan(maceration_end_hour=48.0),
        )
        full = simulate_extraction(self.history(), ExtractionPlan())
        self.assertAlmostEqual(short.skin_contact_hours, 48.0)
        self.assertAlmostEqual(full.skin_contact_hours, 120.0)
        self.assertLess(short.tannin_index, full.tannin_index)
        self.assertLess(short.phenolic_index, full.phenolic_index)

    def test_whole_cluster_fraction_changes_tannin_not_by_label_inference(self):
        destemmed = simulate_extraction(
            self.history(), ExtractionPlan(), whole_cluster_fraction=0.0
        )
        whole_cluster = simulate_extraction(
            self.history(), ExtractionPlan(), whole_cluster_fraction=1.0
        )
        self.assertGreater(whole_cluster.tannin_index, destemmed.tannin_index)

    def test_press_blend_back_adds_tannin_and_phenolics(self):
        free_run = simulate_extraction(
            self.history(),
            ExtractionPlan(press_wine_blend_fraction=0.0, press_severity=0.8),
        )
        blended = simulate_extraction(
            self.history(),
            ExtractionPlan(press_wine_blend_fraction=0.35, press_severity=0.8),
        )
        self.assertEqual(free_run.press_tannin_increment, 0.0)
        self.assertGreater(blended.press_tannin_increment, 0.0)
        self.assertGreater(blended.press_phenolic_increment, 0.0)
        self.assertGreater(blended.tannin_index, free_run.tannin_index)

    def test_events_outside_skin_contact_window_are_not_applied(self):
        result = simulate_extraction(
            self.history(),
            ExtractionPlan(
                maceration_end_hour=48.0,
                cap_management_events=(
                    CapManagementEvent(24.0, 0.5, "pump-over"),
                    CapManagementEvent(72.0, 1.0, "pump-over"),
                ),
            ),
        )
        self.assertEqual(result.cap_event_count, 1)
        self.assertEqual(result.ignored_cap_event_count, 1)
        self.assertTrue(result.warnings)

    def test_invalid_extraction_plan_fails(self):
        with self.assertRaises(ExtractionConstraintError):
            ExtractionPlan(maceration_start_hour=72.0, maceration_end_hour=48.0)
        with self.assertRaises(ExtractionConstraintError):
            CapManagementEvent(hour=10.0, intensity=1.2)
        with self.assertRaises(ExtractionConstraintError):
            ExtractionPlan(press_wine_blend_fraction=1.1)

    def test_runtime_cap_management_requires_event_schedule(self):
        unresolved = apply_winemaking_decisions(
            {"cap-management": "punchdown"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
        )
        self.assertEqual(unresolved.applications[0].status, "requires_measurement")
        self.assertEqual(unresolved.extraction_plan.cap_management_events, ())

        applied = apply_winemaking_decisions(
            {"cap-management": "punchdown"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            runtime_inputs=DecisionRuntimeInputs(
                cap_management_events=((24.0, 0.7), (48.0, 0.6))
            ),
        )
        self.assertEqual(applied.applications[0].status, "applied")
        self.assertEqual(len(applied.extraction_plan.cap_management_events), 2)
        self.assertTrue(
            all(event.method == "punchdown" for event in applied.extraction_plan.cap_management_events)
        )

    def test_runtime_maceration_duration_requires_explicit_end_hour(self):
        unresolved = apply_winemaking_decisions(
            {"maceration-duration": "extended"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
        )
        self.assertEqual(unresolved.applications[0].status, "requires_measurement")

        applied = apply_winemaking_decisions(
            {"maceration-duration": "extended"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            runtime_inputs=DecisionRuntimeInputs(
                maceration_start_hour=0.0,
                maceration_end_hour=240.0,
            ),
        )
        self.assertEqual(applied.extraction_plan.maceration_end_hour, 240.0)

    def test_runtime_press_fraction_requires_blend_and_severity(self):
        unresolved = apply_winemaking_decisions(
            {"press-fraction": "firm-press"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            runtime_inputs=DecisionRuntimeInputs(press_wine_blend_fraction=0.25),
        )
        self.assertEqual(unresolved.applications[0].status, "requires_measurement")

        applied = apply_winemaking_decisions(
            {"press-fraction": "firm-press"},
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            runtime_inputs=DecisionRuntimeInputs(
                press_wine_blend_fraction=0.25,
                press_severity=0.85,
            ),
        )
        self.assertAlmostEqual(applied.extraction_plan.press_wine_blend_fraction, 0.25)
        self.assertAlmostEqual(applied.extraction_plan.press_severity, 0.85)

    def test_runtime_extraction_plan_can_be_simulated_against_actual_history(self):
        runtime = apply_winemaking_decisions(
            {
                "destemming": "partial",
                "cap-management": "gentle-pumpover",
                "maceration-duration": "standard",
                "press-fraction": "gentle-press",
            },
            must=self.must(),
            fermentation_plan=FermentationPlan(),
            runtime_inputs=DecisionRuntimeInputs(
                partial_whole_cluster_fraction=0.30,
                cap_management_events=((24.0, 0.4), (48.0, 0.4), (72.0, 0.4)),
                maceration_end_hour=96.0,
                press_wine_blend_fraction=0.15,
                press_severity=0.40,
            ),
        )
        result = simulate_extraction(
            self.history(),
            runtime.extraction_plan,
            whole_cluster_fraction=runtime.fermentation_plan.alcoholic_params.whole_cluster_fraction,
            source_extraction_potential=runtime.must.source_extraction_potential,
        )
        self.assertAlmostEqual(result.skin_contact_hours, 96.0)
        self.assertEqual(result.cap_event_count, 3)
        self.assertGreater(result.tannin_index, 0.0)


if __name__ == "__main__":
    unittest.main()
