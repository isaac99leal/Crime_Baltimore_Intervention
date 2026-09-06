from __future__ import annotations

import unittest

from sommelier_v2.knowledge.packaging import (
    PackagingPlan,
    assess_packaging,
)
from sommelier_v2.knowledge.smoke_taint import (
    SmokeTaintConstraintError,
    assess_smoke_markers,
    supported_smoke_guide_cultivars,
)


class PackagingAndSmokeTests(unittest.TestCase):
    def test_measured_dissolved_oxygen_changes_ageing_modifier(self):
        low = assess_packaging(
            ph=3.35,
            free_so2_mg_l=30.0,
            plan=PackagingPlan(
                prebottling_dissolved_oxygen_mg_l=0.2,
                closure_oxygen_exposure_prior=0.2,
                tartrate_test_status="tested_stable",
            ),
        )
        high = assess_packaging(
            ph=3.35,
            free_so2_mg_l=30.0,
            plan=PackagingPlan(
                prebottling_dissolved_oxygen_mg_l=4.0,
                closure_oxygen_exposure_prior=0.2,
                tartrate_test_status="tested_stable",
            ),
        )
        self.assertEqual(low.prebottling_oxygen_risk_index, 0.0)
        self.assertEqual(high.prebottling_oxygen_risk_index, 1.0)
        self.assertGreater(high.ageing_oxygen_modifier, low.ageing_oxygen_modifier)
        self.assertGreater(
            high.free_so2_cost_guide_upper_mg_l or 0.0,
            low.free_so2_cost_guide_upper_mg_l or 0.0,
        )

    def test_closure_behavior_is_not_inferred_when_unknown(self):
        result = assess_packaging(
            ph=3.4,
            free_so2_mg_l=25.0,
            plan=PackagingPlan(prebottling_dissolved_oxygen_mg_l=0.3),
        )
        self.assertIsNone(result.closure_oxygen_exposure_prior)
        self.assertFalse(result.oxygen_assessment_complete)
        self.assertTrue(any("closure oxygen exposure is unknown" in w.lower() for w in result.warnings))

    def test_cold_stabilization_does_not_prove_stability(self):
        result = assess_packaging(
            ph=3.3,
            free_so2_mg_l=25.0,
            plan=PackagingPlan(
                cold_stabilization_performed=True,
                tartrate_test_status="unknown",
            ),
        )
        self.assertIsNone(result.tartrate_physical_instability_risk)
        self.assertTrue(any("does not prove" in w.lower() for w in result.warnings))

    def test_tested_tartrate_instability_is_physical_not_microbiological(self):
        result = assess_packaging(
            ph=3.3,
            free_so2_mg_l=25.0,
            plan=PackagingPlan(tartrate_test_status="tested_unstable"),
        )
        self.assertEqual(result.tartrate_physical_instability_risk, 1.0)
        self.assertTrue(any("physical stability" in w.lower() for w in result.warnings))
        self.assertTrue(any("not microbial" in w.lower() for w in result.warnings))

    def test_smoke_guides_are_cultivar_specific(self):
        self.assertEqual(
            supported_smoke_guide_cultivars(),
            ("Chardonnay", "Pinot Noir", "Shiraz"),
        )
        with self.assertRaises(SmokeTaintConstraintError):
            assess_smoke_markers(cultivar="Cabernet Sauvignon", markers_ug_kg={"guaiacol": 5.0})

    def test_pinot_marker_panel_uses_pinot_thresholds(self):
        below = assess_smoke_markers(
            cultivar="Pinot Noir",
            markers_ug_kg={"guaiacol": 1.0},
        )
        high = assess_smoke_markers(
            cultivar="Pinot Noir",
            markers_ug_kg={"guaiacol": 3.5},
        )
        self.assertEqual(
            below.marker_results[0].guide_band,
            "below_published_moderate_guide",
        )
        self.assertEqual(
            high.marker_results[0].guide_band,
            "at_or_above_published_high_guide",
        )
        self.assertIn("pinot", high.cultivar.lower())
        self.assertTrue(high.ageing_expression_possible)
        self.assertTrue(any("not universal sensory cutoffs" in w.lower() for w in high.warnings))

    def test_smoke_marker_names_must_exist_in_source_panel(self):
        with self.assertRaises(SmokeTaintConstraintError):
            assess_smoke_markers(
                cultivar="Chardonnay",
                markers_ug_kg={"inventedMarker": 1.0},
            )

    def test_equal_moderate_and_high_guide_does_not_invent_middle_band(self):
        result = assess_smoke_markers(
            cultivar="Pinot Noir",
            markers_ug_kg={"pCresol": 0.5},
        )
        self.assertEqual(
            result.marker_results[0].guide_band,
            "at_or_above_published_high_guide",
        )


if __name__ == "__main__":
    unittest.main()
