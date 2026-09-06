from __future__ import annotations

import unittest

from sommelier_v2.knowledge.cellar_pipeline import (
    CellarHandoffInputs,
    CellarPipelineConstraintError,
    CellarPipelinePlan,
    run_cellar_pipeline,
)
from sommelier_v2.knowledge.extraction_process import ExtractionPlan
from sommelier_v2.knowledge.fermentation_engine import MalolacticParams
from sommelier_v2.knowledge.fermentation_process import FermentationPlan, MustComposition
from sommelier_v2.knowledge.maturation_process import MaturationPlan
from sommelier_v2.knowledge.packaging import PackagingPlan


class CellarPipelineTests(unittest.TestCase):
    @staticmethod
    def must(*, malic: float = 1.0) -> MustComposition:
        return MustComposition(
            volume_l=500.0,
            sugar_g_l=12.0,
            yan_mg_l=240.0,
            ph=3.45,
            titratable_acidity_g_l=6.0,
            malic_acid_g_l=malic,
            temp_c=24.0,
            free_so2_mg_l=0.0,
            source_extraction_potential=0.65,
        )

    @staticmethod
    def ferment_plan(**kwargs) -> FermentationPlan:
        defaults = dict(
            post_fermentation_free_so2_mg_l=28.0,
            max_hours=240.0,
        )
        defaults.update(kwargs)
        return FermentationPlan(**defaults)

    def test_pipeline_runs_fermentation_extraction_maturation_and_packaging(self):
        result = run_cellar_pipeline(
            must=self.must(),
            fermentation_plan=self.ferment_plan(),
            extraction_plan=ExtractionPlan(maceration_end_hour=48.0),
            maturation_plan=MaturationPlan(
                duration_days=30.0,
                vessel_oxygen_transfer_mg_l_month=0.5,
                headspace_oxygen_exposure_mg_l_month=0.1,
            ),
            pipeline_plan=CellarPipelinePlan(run_extraction=True, run_maturation=True),
            handoff=CellarHandoffInputs(maturation_dissolved_oxygen_mg_l=0.3),
        )
        self.assertTrue(result.fermentation.alcoholic_completed)
        self.assertIsNotNone(result.extraction)
        self.assertIsNotNone(result.maturation)
        self.assertGreater(result.extraction.tannin_index if result.extraction else 0.0, 0.0)
        self.assertEqual(result.packaging_free_so2_mg_l, result.maturation.final_state.free_so2_mg_l)

    def test_maturation_requires_explicit_so2_handoff(self):
        with self.assertRaises(CellarPipelineConstraintError):
            run_cellar_pipeline(
                must=self.must(),
                fermentation_plan=FermentationPlan(max_hours=240.0),
                maturation_plan=MaturationPlan(duration_days=10.0),
                pipeline_plan=CellarPipelinePlan(run_maturation=True),
                handoff=CellarHandoffInputs(
                    maturation_tannin_index=0.0,
                    maturation_phenolic_index=0.0,
                    maturation_anthocyanin_index=0.0,
                ),
            )

    def test_explicit_postfermentation_so2_can_seed_maturation(self):
        result = run_cellar_pipeline(
            must=self.must(),
            fermentation_plan=self.ferment_plan(post_fermentation_free_so2_mg_l=31.0),
            maturation_plan=MaturationPlan(duration_days=0.0),
            pipeline_plan=CellarPipelinePlan(run_maturation=True),
            handoff=CellarHandoffInputs(
                maturation_tannin_index=0.0,
                maturation_phenolic_index=0.0,
                maturation_anthocyanin_index=0.0,
            ),
        )
        self.assertIsNotNone(result.maturation)
        self.assertAlmostEqual(result.maturation.final_state.free_so2_mg_l, 31.0)

    def test_maturation_without_extraction_requires_explicit_structure(self):
        with self.assertRaises(CellarPipelineConstraintError):
            run_cellar_pipeline(
                must=self.must(),
                fermentation_plan=self.ferment_plan(),
                maturation_plan=MaturationPlan(duration_days=10.0),
                pipeline_plan=CellarPipelinePlan(run_maturation=True),
            )

        result = run_cellar_pipeline(
            must=self.must(),
            fermentation_plan=self.ferment_plan(),
            maturation_plan=MaturationPlan(duration_days=10.0),
            pipeline_plan=CellarPipelinePlan(run_maturation=True),
            handoff=CellarHandoffInputs(
                maturation_tannin_index=0.10,
                maturation_phenolic_index=0.15,
                maturation_anthocyanin_index=0.08,
            ),
        )
        self.assertAlmostEqual(result.maturation.history[0].tannin_index, 0.10)

    def test_extraction_is_single_source_for_maturation_structure(self):
        with self.assertRaises(CellarPipelineConstraintError):
            run_cellar_pipeline(
                must=self.must(),
                fermentation_plan=self.ferment_plan(),
                extraction_plan=ExtractionPlan(maceration_end_hour=24.0),
                maturation_plan=MaturationPlan(duration_days=10.0),
                pipeline_plan=CellarPipelinePlan(run_extraction=True, run_maturation=True),
                handoff=CellarHandoffInputs(
                    maturation_tannin_index=0.2,
                    maturation_phenolic_index=0.2,
                    maturation_anthocyanin_index=0.2,
                ),
            )

    def test_maturation_dissolved_oxygen_is_not_a_bottling_measurement(self):
        result = run_cellar_pipeline(
            must=self.must(),
            fermentation_plan=self.ferment_plan(),
            maturation_plan=MaturationPlan(
                duration_days=10.0,
                vessel_oxygen_transfer_mg_l_month=0.2,
                headspace_oxygen_exposure_mg_l_month=0.05,
            ),
            packaging_plan=PackagingPlan(closure_oxygen_exposure_prior=0.2),
            pipeline_plan=CellarPipelinePlan(run_maturation=True),
            handoff=CellarHandoffInputs(
                maturation_dissolved_oxygen_mg_l=0.4,
                maturation_tannin_index=0.0,
                maturation_phenolic_index=0.0,
                maturation_anthocyanin_index=0.0,
            ),
        )
        self.assertIsNotNone(result.maturation.final_state.dissolved_oxygen_mg_l)
        self.assertIsNone(result.packaging.prebottling_oxygen_risk_index)
        self.assertFalse(result.packaging.oxygen_assessment_complete)

    def test_explicit_packaging_so2_supersedes_upstream_value(self):
        result = run_cellar_pipeline(
            must=self.must(),
            fermentation_plan=self.ferment_plan(post_fermentation_free_so2_mg_l=25.0),
            handoff=CellarHandoffInputs(packaging_free_so2_mg_l=42.0),
        )
        self.assertEqual(result.packaging_free_so2_mg_l, 42.0)

    def test_mlf_final_ph_propagates_to_packaging(self):
        result = run_cellar_pipeline(
            must=self.must(malic=1.0),
            fermentation_plan=self.ferment_plan(
                malolactic=True,
                malolactic_params=MalolacticParams(
                    base_malic_rate_g_l_day=1.0,
                    target_malic_g_l=0.10,
                ),
                mlf_start_temp_c=20.0,
                mlf_max_days=20.0,
            ),
        )
        self.assertTrue(result.fermentation.malolactic_completed)
        self.assertGreater(result.final_ph, self.must().ph)

    def test_configured_extraction_cannot_be_silently_skipped(self):
        with self.assertRaises(CellarPipelineConstraintError):
            run_cellar_pipeline(
                must=self.must(),
                fermentation_plan=self.ferment_plan(),
                selections={"maceration-duration": "configured"},
                pipeline_plan=CellarPipelinePlan(run_extraction=False),
            )

    def test_configured_maturation_cannot_be_silently_skipped(self):
        with self.assertRaises(CellarPipelineConstraintError):
            run_cellar_pipeline(
                must=self.must(),
                fermentation_plan=self.ferment_plan(),
                selections={"maturation-duration": "configured"},
                pipeline_plan=CellarPipelinePlan(run_maturation=False),
            )


if __name__ == "__main__":
    unittest.main()
