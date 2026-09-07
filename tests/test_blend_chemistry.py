from __future__ import annotations

import math
import unittest

from sommelier_v2.knowledge.blend_chemistry import (
    BlendChemistryComponent,
    BlendChemistryConstraintError,
    BlendPostMixMeasurements,
    blend_chemistry,
)


class BlendChemistryTests(unittest.TestCase):
    @staticmethod
    def components() -> tuple[BlendChemistryComponent, ...]:
        return (
            BlendChemistryComponent(
                source_id="lot-a",
                draw_l=100.0,
                ethanol_pct=12.0,
                residual_sugar_g_l=2.0,
                malic_acid_g_l=2.0,
                lactic_acid_g_l=0.2,
                tartaric_acid_g_l=3.0,
                volatile_acidity_g_l=0.5,
                total_so2_mg_l=80.0,
                dissolved_oxygen_mg_l=1.0,
                ph=3.10,
                free_so2_mg_l=25.0,
                titratable_acidity_g_l=6.5,
            ),
            BlendChemistryComponent(
                source_id="lot-b",
                draw_l=50.0,
                ethanol_pct=15.0,
                residual_sugar_g_l=8.0,
                malic_acid_g_l=1.0,
                lactic_acid_g_l=1.0,
                tartaric_acid_g_l=4.0,
                volatile_acidity_g_l=0.7,
                total_so2_mg_l=120.0,
                dissolved_oxygen_mg_l=2.0,
                ph=3.70,
                free_so2_mg_l=10.0,
                titratable_acidity_g_l=4.0,
            ),
        )

    def test_conserves_linear_component_mass(self) -> None:
        result = blend_chemistry(self.components(), operation_oxygen_delta_mg=0.0)

        self.assertEqual(result.volume_l, 150.0)
        self.assertAlmostEqual(result.ethanol_l or 0.0, 19.5)
        self.assertAlmostEqual(result.ethanol_pct or 0.0, 13.0)

        self.assertAlmostEqual(result.residual_sugar_g or 0.0, 600.0)
        self.assertAlmostEqual(result.residual_sugar_g_l or 0.0, 4.0)
        self.assertAlmostEqual(result.malic_acid_g or 0.0, 250.0)
        self.assertAlmostEqual(result.malic_acid_g_l or 0.0, 250.0 / 150.0)
        self.assertAlmostEqual(result.lactic_acid_g or 0.0, 70.0)
        self.assertAlmostEqual(result.lactic_acid_g_l or 0.0, 70.0 / 150.0)
        self.assertAlmostEqual(result.tartaric_acid_g or 0.0, 500.0)
        self.assertAlmostEqual(result.tartaric_acid_g_l or 0.0, 500.0 / 150.0)
        self.assertAlmostEqual(result.volatile_acidity_g or 0.0, 85.0)
        self.assertAlmostEqual(result.volatile_acidity_g_l or 0.0, 85.0 / 150.0)

        self.assertAlmostEqual(result.input_total_so2_mg or 0.0, 14_000.0)
        self.assertAlmostEqual(result.pre_reaction_total_so2_mg_l or 0.0, 14_000.0 / 150.0)
        self.assertIn("ethanol", result.conserved_fields)
        self.assertIn("residual_sugar_g_l", result.conserved_fields)
        self.assertIn("total_so2_mg_l", result.conserved_fields)

    def test_pH_free_so2_and_ta_are_never_volume_averaged(self) -> None:
        result = blend_chemistry(self.components(), operation_oxygen_delta_mg=0.0)

        self.assertIsNone(result.ph)
        self.assertIsNone(result.free_so2_mg_l)
        self.assertIsNone(result.titratable_acidity_g_l)
        self.assertIn("ph", result.unresolved_fields)
        self.assertIn("free_so2_mg_l", result.unresolved_fields)
        self.assertIn("titratable_acidity_g_l", result.unresolved_fields)
        warning_text = " ".join(result.warnings)
        self.assertIn("not volume-averaged", warning_text)

    def test_post_mix_measurements_are_authoritative_observations(self) -> None:
        result = blend_chemistry(
            self.components(),
            operation_oxygen_delta_mg=0.0,
            post_mix=BlendPostMixMeasurements(
                ph=3.42,
                free_so2_mg_l=18.0,
                titratable_acidity_g_l=5.7,
                total_so2_mg_l=92.0,
                dissolved_oxygen_mg_l=0.75,
            ),
        )

        self.assertEqual(result.ph, 3.42)
        self.assertEqual(result.free_so2_mg_l, 18.0)
        self.assertEqual(result.titratable_acidity_g_l, 5.7)
        self.assertEqual(result.measured_total_so2_mg_l, 92.0)
        self.assertEqual(result.dissolved_oxygen_mg_l, 0.75)
        self.assertIn("ph", result.measured_fields)
        self.assertIn("dissolved_oxygen_mg_l", result.measured_fields)
        self.assertTrue(result.oxygen_model_complete)
        self.assertNotEqual(result.modeled_dissolved_oxygen_mg_l, result.dissolved_oxygen_mg_l)

    def test_operation_oxygen_delta_is_absolute_mass_not_concentration(self) -> None:
        result = blend_chemistry(self.components(), operation_oxygen_delta_mg=30.0)
        # Source mass = 100 L*1 mg/L + 50 L*2 mg/L = 200 mg.
        # Plus 30 mg operation pickup = 230 mg / 150 L.
        self.assertAlmostEqual(result.modeled_dissolved_oxygen_mg_l or 0.0, 230.0 / 150.0)
        self.assertAlmostEqual(result.dissolved_oxygen_mg_l or 0.0, 230.0 / 150.0)
        self.assertTrue(result.oxygen_model_complete)

    def test_unknown_operation_oxygen_delta_does_not_mean_zero(self) -> None:
        result = blend_chemistry(self.components())
        self.assertIsNone(result.modeled_dissolved_oxygen_mg_l)
        self.assertIsNone(result.dissolved_oxygen_mg_l)
        self.assertFalse(result.oxygen_model_complete)
        self.assertIn("dissolved_oxygen_mg_l", result.unresolved_fields)
        self.assertTrue(any("oxygen pickup/removal is unknown" in warning for warning in result.warnings))

        explicit_zero = blend_chemistry(self.components(), operation_oxygen_delta_mg=0.0)
        self.assertTrue(explicit_zero.oxygen_model_complete)
        self.assertAlmostEqual(explicit_zero.dissolved_oxygen_mg_l or 0.0, 200.0 / 150.0)

    def test_missing_one_source_measurement_propagates_unknown_only_for_that_balance(self) -> None:
        a, b = self.components()
        incomplete = (
            a,
            BlendChemistryComponent(
                source_id=b.source_id,
                draw_l=b.draw_l,
                ethanol_pct=b.ethanol_pct,
                residual_sugar_g_l=None,
                malic_acid_g_l=b.malic_acid_g_l,
                lactic_acid_g_l=b.lactic_acid_g_l,
                tartaric_acid_g_l=b.tartaric_acid_g_l,
                volatile_acidity_g_l=b.volatile_acidity_g_l,
                total_so2_mg_l=b.total_so2_mg_l,
                dissolved_oxygen_mg_l=b.dissolved_oxygen_mg_l,
            ),
        )
        result = blend_chemistry(incomplete, operation_oxygen_delta_mg=0.0)

        self.assertIsNone(result.residual_sugar_g)
        self.assertIsNone(result.residual_sugar_g_l)
        self.assertIn("residual_sugar_g_l", result.unresolved_fields)
        self.assertAlmostEqual(result.ethanol_pct or 0.0, 13.0)
        self.assertIsNotNone(result.malic_acid_g_l)

    def test_measured_total_so2_remains_separate_from_pre_reaction_mass_balance(self) -> None:
        result = blend_chemistry(
            self.components(),
            operation_oxygen_delta_mg=0.0,
            post_mix=BlendPostMixMeasurements(total_so2_mg_l=70.0),
        )
        self.assertAlmostEqual(result.pre_reaction_total_so2_mg_l or 0.0, 14_000.0 / 150.0)
        self.assertEqual(result.measured_total_so2_mg_l, 70.0)
        self.assertNotEqual(result.pre_reaction_total_so2_mg_l, result.measured_total_so2_mg_l)

    def test_duplicate_source_rows_are_rejected(self) -> None:
        row = self.components()[0]
        with self.assertRaises(BlendChemistryConstraintError):
            blend_chemistry((row, row), operation_oxygen_delta_mg=0.0)

    def test_oxygen_removal_cannot_exceed_available_source_oxygen(self) -> None:
        with self.assertRaises(BlendChemistryConstraintError):
            blend_chemistry(self.components(), operation_oxygen_delta_mg=-200.01)

    def test_nonfinite_and_impossible_inputs_fail_closed(self) -> None:
        with self.assertRaises(BlendChemistryConstraintError):
            BlendChemistryComponent(source_id="x", draw_l=math.inf)
        with self.assertRaises(BlendChemistryConstraintError):
            BlendChemistryComponent(source_id="x", draw_l=1.0, ethanol_pct=31.0)
        with self.assertRaises(BlendChemistryConstraintError):
            BlendPostMixMeasurements(ph=5.1)


if __name__ == "__main__":
    unittest.main()
