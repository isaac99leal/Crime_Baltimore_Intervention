from __future__ import annotations

import unittest

from sommelier_v2.knowledge.fortification_chemistry import (
    FortificationConstraintError,
    FortificationLiquid,
    FortificationPostMixMeasurements,
    fortify_liquid,
    ideal_spirit_volume_for_target_abv,
)


class FortificationChemistryTests(unittest.TestCase):
    @staticmethod
    def base() -> FortificationLiquid:
        return FortificationLiquid(
            source_id="base-wine",
            volume_l=100.0,
            ethanol_pct=10.0,
            residual_sugar_g_l=100.0,
            malic_acid_g_l=2.0,
            lactic_acid_g_l=0.5,
            tartaric_acid_g_l=3.0,
            volatile_acidity_g_l=0.4,
            total_so2_mg_l=80.0,
            ph=3.25,
            free_so2_mg_l=20.0,
            titratable_acidity_g_l=6.0,
        )

    @staticmethod
    def spirit() -> FortificationLiquid:
        return FortificationLiquid(
            source_id="grape-spirit",
            volume_l=20.0,
            ethanol_pct=80.0,
            residual_sugar_g_l=0.0,
            malic_acid_g_l=0.0,
            lactic_acid_g_l=0.0,
            tartaric_acid_g_l=0.0,
            volatile_acidity_g_l=0.0,
            total_so2_mg_l=0.0,
            ph=4.0,
            free_so2_mg_l=0.0,
            titratable_acidity_g_l=0.0,
        )

    def test_ideal_additive_basis_conserves_ethanol_and_sugar(self) -> None:
        result = fortify_liquid(self.base(), self.spirit())
        self.assertEqual(result.ideal_additive_volume_l, 120.0)
        self.assertAlmostEqual(result.ethanol_equivalent_l, 26.0)
        self.assertAlmostEqual(result.ideal_additive_ethanol_pct, 26.0 / 120.0 * 100.0)
        self.assertEqual(result.residual_sugar_g, 10_000.0)
        self.assertAlmostEqual(result.ideal_additive_residual_sugar_g_l, 10_000.0 / 120.0)
        self.assertIsNone(result.volume_corrected_ethanol_pct)
        self.assertIn("measured_final_volume_l", result.unresolved_fields)
        self.assertTrue(any("ideal additive-volume" in warning for warning in result.warnings))

    def test_measured_final_volume_separates_contraction_from_mass_balance(self) -> None:
        result = fortify_liquid(
            self.base(),
            self.spirit(),
            post_mix=FortificationPostMixMeasurements(final_volume_l=118.0),
        )
        self.assertEqual(result.volume_delta_l, -2.0)
        self.assertAlmostEqual(result.volume_corrected_ethanol_pct or 0.0, 26.0 / 118.0 * 100.0)
        self.assertAlmostEqual(result.volume_corrected_residual_sugar_g_l or 0.0, 10_000.0 / 118.0)
        self.assertAlmostEqual(result.volume_corrected_malic_acid_g_l or 0.0, 200.0 / 118.0)
        self.assertTrue(any("volume-corrected" in warning for warning in result.warnings))

    def test_linear_solutes_conserve_absolute_mass(self) -> None:
        result = fortify_liquid(self.base(), self.spirit())
        self.assertEqual(result.malic_acid_g, 200.0)
        self.assertEqual(result.lactic_acid_g, 50.0)
        self.assertEqual(result.tartaric_acid_g, 300.0)
        self.assertEqual(result.volatile_acidity_g, 40.0)
        self.assertEqual(result.input_total_so2_mg, 8_000.0)
        self.assertAlmostEqual(result.ideal_additive_total_so2_mg_l or 0.0, 8_000.0 / 120.0)

    def test_ph_free_so2_and_ta_are_measurement_only(self) -> None:
        result = fortify_liquid(self.base(), self.spirit())
        self.assertIsNone(result.ph)
        self.assertIsNone(result.free_so2_mg_l)
        self.assertIsNone(result.titratable_acidity_g_l)
        for field in ("ph", "free_so2_mg_l", "titratable_acidity_g_l"):
            self.assertIn(field, result.unresolved_fields)

        measured = fortify_liquid(
            self.base(),
            self.spirit(),
            post_mix=FortificationPostMixMeasurements(
                final_volume_l=118.0,
                ph=3.48,
                free_so2_mg_l=16.0,
                titratable_acidity_g_l=5.2,
            ),
        )
        self.assertEqual(measured.ph, 3.48)
        self.assertEqual(measured.free_so2_mg_l, 16.0)
        self.assertEqual(measured.titratable_acidity_g_l, 5.2)

    def test_unknown_source_solute_stays_unknown_not_zero(self) -> None:
        spirit = FortificationLiquid(
            source_id="spirit",
            volume_l=20.0,
            ethanol_pct=80.0,
            residual_sugar_g_l=0.0,
            malic_acid_g_l=None,
        )
        result = fortify_liquid(self.base(), spirit)
        self.assertIsNone(result.malic_acid_g)
        self.assertIsNone(result.ideal_additive_malic_acid_g_l)
        self.assertIn("malic_acid_g_l", result.unresolved_fields)

    def test_ideal_target_solver_is_exact_on_its_declared_basis(self) -> None:
        spirit_volume = ideal_spirit_volume_for_target_abv(
            base_volume_l=100.0,
            base_ethanol_pct=10.0,
            spirit_ethanol_pct=80.0,
            target_ethanol_pct=20.0,
        )
        self.assertAlmostEqual(spirit_volume, 100.0 / 6.0)
        result = fortify_liquid(
            self.base(),
            FortificationLiquid(
                source_id="target-spirit",
                volume_l=spirit_volume,
                ethanol_pct=80.0,
                residual_sugar_g_l=0.0,
            ),
        )
        self.assertAlmostEqual(result.ideal_additive_ethanol_pct, 20.0)

    def test_target_solver_requires_target_between_base_and_spirit(self) -> None:
        for target in (5.0, 10.0, 80.0, 85.0):
            if target == 10.0:
                self.assertEqual(
                    ideal_spirit_volume_for_target_abv(
                        base_volume_l=100.0,
                        base_ethanol_pct=10.0,
                        spirit_ethanol_pct=80.0,
                        target_ethanol_pct=target,
                    ),
                    0.0,
                )
            else:
                with self.assertRaises(FortificationConstraintError):
                    ideal_spirit_volume_for_target_abv(
                        base_volume_l=100.0,
                        base_ethanol_pct=10.0,
                        spirit_ethanol_pct=80.0,
                        target_ethanol_pct=target,
                    )

    def test_spirit_must_raise_abv_and_sources_must_be_distinct(self) -> None:
        with self.assertRaises(FortificationConstraintError):
            fortify_liquid(
                self.base(),
                FortificationLiquid(
                    source_id="weak-spirit",
                    volume_l=10.0,
                    ethanol_pct=9.0,
                    residual_sugar_g_l=0.0,
                ),
            )
        with self.assertRaises(FortificationConstraintError):
            fortify_liquid(
                self.base(),
                FortificationLiquid(
                    source_id="base-wine",
                    volume_l=10.0,
                    ethanol_pct=80.0,
                    residual_sugar_g_l=0.0,
                ),
            )

    def test_impossible_measured_volume_fails_ethanol_conservation(self) -> None:
        with self.assertRaises(FortificationConstraintError):
            fortify_liquid(
                self.base(),
                self.spirit(),
                post_mix=FortificationPostMixMeasurements(final_volume_l=20.0),
            )

    def test_boolean_and_numeric_string_inputs_fail_closed(self) -> None:
        with self.assertRaises(FortificationConstraintError):
            FortificationLiquid(
                source_id="x",
                volume_l=True,  # type: ignore[arg-type]
                ethanol_pct=80.0,
                residual_sugar_g_l=0.0,
            )
        with self.assertRaises(FortificationConstraintError):
            FortificationLiquid(
                source_id="x",
                volume_l=1.0,
                ethanol_pct="80",  # type: ignore[arg-type]
                residual_sugar_g_l=0.0,
            )
        with self.assertRaises(FortificationConstraintError):
            FortificationPostMixMeasurements(final_volume_l="1")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
