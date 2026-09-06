from __future__ import annotations

import unittest

from sommelier_v2.knowledge import (
    VineyardBlock,
    VineyardEngine,
    VineyardYieldAdjustmentRegistry,
)
from sommelier_v2.knowledge.vineyard_legal_constraints import VineyardLegalConstraintRegistry
from sommelier_v2.knowledge.vintage_engine import DailyWeather


class VineyardLegalConstraintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = VineyardLegalConstraintRegistry()
        cls.yield_registry = VineyardYieldAdjustmentRegistry()

    @staticmethod
    def geometry() -> dict[str, object]:
        return {
            "planting_pattern": "rows",
            "row_spacing_m": 1.25,
            "vine_spacing_m": 0.50,
        }

    @staticmethod
    def management(style: str = "red") -> dict[str, object]:
        return {
            "wine_style": style,
            "pruning_system": "guyot_simple",
            "retained_buds_per_vine": 8,
            "fruiting_shoots_per_vine": 8,
            "support_system": "trellis",
            "canopy_height_m": 0.75,
            "parcel_crop_load_kg_ha": 9000.0 if style == "red" else 10500.0,
        }

    @staticmethod
    def block_management(style: str = "red") -> dict[str, object]:
        return {
            "pruning_system": "guyot_simple",
            "retained_buds_per_vine": 8,
            "fruiting_shoots_per_vine": 8,
            "support_system": "trellis",
            "canopy_height_m": 0.75,
            "parcel_crop_load_kg_ha": 9000.0 if style == "red" else 10500.0,
            "dead_missing_vine_fraction": 0.20,
        }

    def assess(self, appellation: str, *, style: str = "red", **overrides):
        values = {
            "country": "France",
            "appellation": appellation,
            "vine_density_per_ha": 9000,
            "irrigation_mm_per_week": 0.0,
            **self.geometry(),
            **self.management(style),
        }
        values.update(overrides)
        return self.registry.assess(**values)

    @staticmethod
    def weather() -> list[DailyWeather]:
        return [
            DailyWeather(
                day_of_year=doy,
                tmin_c=16.0,
                tmax_c=31.0,
                rain_mm=0.5,
                humidity_pct=50.0,
                solar_mj_m2=22.0,
                wind_m_s=2.0,
            )
            for doy in range(80, 311)
        ]

    def test_reviewed_constraints_resolve_with_management_matrix(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            row = self.registry.resolve(country="France", appellation=appellation)
            self.assertIsNotNone(row)
            self.assertEqual(row.min_vine_density_per_ha, 9000)
            self.assertIs(row.irrigation_prohibited, True)
            self.assertEqual(row.allowed_planting_patterns, ("rows", "foule"))
            self.assertEqual(row.max_row_spacing_m, 1.25)
            self.assertEqual(row.min_vine_spacing_m, 0.50)
            self.assertEqual(row.min_foule_vine_spacing_m_exclusive, 0.50)
            self.assertEqual(row.pruning_rule_map("red")["guyot_simple"], 8)
            self.assertEqual(row.pruning_rule_map("white")["cordon_royat"], 10)
            self.assertEqual(row.crop_load_limit("red"), 9000)
            self.assertEqual(row.crop_load_limit("white"), 10500)
            self.assertEqual(row.min_trellised_canopy_height_to_row_spacing_ratio, 0.60)

    def test_complete_positive_red_path(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            decision = self.assess(appellation)
            self.assertIs(decision.satisfied, True)
            self.assertEqual(decision.status, "reviewed_vineyard_constraints_satisfied")

    def test_density_and_irrigation_boundaries(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            self.assertIs(self.assess(appellation, vine_density_per_ha=9000).satisfied, True)
            self.assertIs(self.assess(appellation, vine_density_per_ha=8999).satisfied, False)
            self.assertIs(self.assess(appellation, irrigation_mm_per_week=0.0).satisfied, True)
            self.assertIs(self.assess(appellation, irrigation_mm_per_week=0.01).satisfied, False)

    def test_rows_use_inclusive_half_meter_vine_spacing(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            exact = self.assess(appellation, row_spacing_m=1.25, vine_spacing_m=0.50)
            wide = self.assess(appellation, row_spacing_m=1.251)
            tight = self.assess(appellation, vine_spacing_m=0.499)
            self.assertIs(exact.satisfied, True)
            self.assertIs(wide.satisfied, False)
            self.assertIs(tight.satisfied, False)

    def test_foule_uses_strict_greater_than_half_meter_spacing(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            exact_half = self.assess(
                appellation,
                planting_pattern="foule",
                row_spacing_m=None,
                vine_spacing_m=0.50,
                support_system="stake",
                canopy_height_m=None,
            )
            above_half = self.assess(
                appellation,
                planting_pattern="foule",
                row_spacing_m=None,
                vine_spacing_m=0.51,
                support_system="stake",
                canopy_height_m=None,
            )
            self.assertIs(exact_half.satisfied, False)
            self.assertTrue(any("strictly greater" in issue for issue in exact_half.issues))
            self.assertIs(above_half.satisfied, True)

    def test_foule_requires_stake_and_never_row_spacing(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            bad_support = self.assess(
                appellation,
                planting_pattern="foule",
                row_spacing_m=None,
                vine_spacing_m=0.51,
                support_system="trellis",
                canopy_height_m=None,
            )
            self.assertIs(bad_support.satisfied, False)

        engine = VineyardEngine()
        impossible = VineyardBlock(
            id="invalid-foule-row-spacing",
            grape="Pinot Noir",
            area_ha=1.0,
            planting_year=2000,
            country="France",
            region="Bourgogne",
            planting_pattern="foule",
            row_spacing_m=1.0,
            vine_spacing_m=0.51,
        )
        with self.assertRaisesRegex(ValueError, "not applicable"):
            engine.validate_block(impossible, vintage_year=2026)

    def test_red_pruning_ceiling_and_extra_bud_condition(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            self.assertIs(self.assess(appellation, retained_buds_per_vine=8).satisfied, True)
            unresolved = self.assess(appellation, retained_buds_per_vine=9, fruiting_shoots_per_vine=None)
            good = self.assess(appellation, retained_buds_per_vine=9, fruiting_shoots_per_vine=8)
            bad = self.assess(appellation, retained_buds_per_vine=9, fruiting_shoots_per_vine=9)
            self.assertIsNone(unresolved.satisfied)
            self.assertIs(good.satisfied, True)
            self.assertIs(bad.satisfied, False)

    def test_white_pruning_is_system_specific(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            cordon = self.assess(
                appellation,
                style="white",
                pruning_system="cordon_royat",
                retained_buds_per_vine=10,
                fruiting_shoots_per_vine=10,
            )
            bad_guyot = self.assess(
                appellation,
                style="white",
                pruning_system="guyot_simple",
                retained_buds_per_vine=9,
                fruiting_shoots_per_vine=9,
            )
            self.assertIs(cordon.satisfied, True)
            self.assertIs(bad_guyot.satisfied, False)

    def test_fixin_guyot_double_transition_is_not_generalized(self) -> None:
        decision = self.assess(
            "Fixin",
            pruning_system="guyot_double",
            retained_buds_per_vine=10,
            support_system="trellis",
        )
        self.assertIsNone(decision.satisfied)
        self.assertTrue(any("conditional exception" in warning for warning in decision.warnings))

    def test_gobelet_does_not_invent_support_requirement(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            decision = self.assess(
                appellation,
                pruning_system="gobelet",
                retained_buds_per_vine=8,
                fruiting_shoots_per_vine=8,
                support_system=None,
                canopy_height_m=None,
            )
            self.assertIs(decision.satisfied, True)

    def test_trellised_canopy_ratio_boundary(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            exact = self.assess(appellation, row_spacing_m=1.25, canopy_height_m=0.75)
            short = self.assess(appellation, row_spacing_m=1.25, canopy_height_m=0.749)
            self.assertIs(exact.satisfied, True)
            self.assertIs(short.satisfied, False)

    def test_parcel_crop_load_boundaries_are_style_specific(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            self.assertIs(self.assess(appellation, parcel_crop_load_kg_ha=9000).satisfied, True)
            self.assertIs(self.assess(appellation, parcel_crop_load_kg_ha=9000.1).satisfied, False)
            self.assertIs(self.assess(appellation, style="white", parcel_crop_load_kg_ha=10500).satisfied, True)
            self.assertIs(self.assess(appellation, style="white", parcel_crop_load_kg_ha=10500.1).satisfied, False)

    def test_missing_reviewed_management_state_is_unknown(self) -> None:
        decision = self.registry.assess(
            country="France",
            appellation="Fixin",
            wine_style="red",
            vine_density_per_ha=9000,
            irrigation_mm_per_week=0.0,
            **self.geometry(),
        )
        self.assertIsNone(decision.satisfied)
        self.assertEqual(decision.status, "reviewed_vineyard_constraint_unobserved")

    def test_dead_missing_vines_trigger_separate_proportional_yield_reduction(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            threshold = self.yield_registry.assess(
                country="France",
                appellation=appellation,
                dead_missing_vine_fraction=0.20,
            )
            above = self.yield_registry.assess(
                country="France",
                appellation=appellation,
                dead_missing_vine_fraction=0.25,
            )
            self.assertEqual(threshold.multiplier, 1.0)
            self.assertAlmostEqual(above.multiplier, 0.75)
            self.assertTrue(any(item.startswith("threshold-source:") for item in above.evidence))
            self.assertIn("remedy-source:fr_code_rural_d645_4", above.evidence)

    def test_dead_missing_fraction_is_required_for_reviewed_yield_adjustment(self) -> None:
        decision = self.yield_registry.assess(
            country="France",
            appellation="Fixin",
            dead_missing_vine_fraction=None,
        )
        self.assertIsNone(decision.multiplier)
        self.assertEqual(decision.status, "dead_missing_vine_fraction_unobserved")

    def test_physical_management_measurement_ranges_are_validated(self) -> None:
        engine = VineyardEngine()
        block = VineyardBlock(
            id="invalid-missing-fraction",
            grape="Pinot Noir",
            area_ha=1.0,
            planting_year=2000,
            country="France",
            region="Bourgogne",
            dead_missing_vine_fraction=1.01,
        )
        with self.assertRaisesRegex(ValueError, "Dead/missing vine fraction"):
            engine.validate_block(block, vintage_year=2026)

    def test_reviewed_but_unobserved_management_withholds_gi(self) -> None:
        engine = VineyardEngine()
        block = VineyardBlock(
            id="fixin-unobserved-management",
            grape="Pinot Noir",
            area_ha=1.0,
            planting_year=2000,
            country="France",
            region="Bourgogne",
            appellation="Fixin",
            wine_variant="red standard",
            label_scope="regulated_gi",
            vine_density_per_ha=9000,
            irrigation_mm_per_week=0.0,
            planting_pattern="rows",
            row_spacing_m=1.25,
            vine_spacing_m=0.50,
            dead_missing_vine_fraction=0.20,
            target_yield_t_ha=4.0,
        )
        result = engine.simulate(block, self.weather(), vintage_year=2026)
        self.assertFalse(result.label_eligible)
        self.assertTrue(any("compliance is unresolved" in warning for warning in result.warnings))

    def test_missing_dead_vine_measurement_withholds_gi(self) -> None:
        engine = VineyardEngine()
        values = self.block_management()
        values.pop("dead_missing_vine_fraction")
        block = VineyardBlock(
            id="fixin-unobserved-missing-vines",
            grape="Pinot Noir",
            area_ha=1.0,
            planting_year=2000,
            country="France",
            region="Bourgogne",
            appellation="Fixin",
            wine_variant="red standard",
            label_scope="regulated_gi",
            vine_density_per_ha=9000,
            irrigation_mm_per_week=0.0,
            planting_pattern="rows",
            row_spacing_m=1.25,
            vine_spacing_m=0.50,
            target_yield_t_ha=4.0,
            **values,
        )
        result = engine.simulate(block, self.weather(), vintage_year=2026)
        self.assertFalse(result.label_eligible)
        self.assertTrue(any("yield adjustment is unresolved" in warning for warning in result.warnings))

    def test_dead_vine_adjustment_is_applied_by_full_engine(self) -> None:
        engine = VineyardEngine()
        block = VineyardBlock(
            id="fixin-dead-vine-yield",
            grape="Pinot Noir",
            area_ha=1.0,
            planting_year=2000,
            country="France",
            region="Bourgogne",
            appellation="Fixin",
            wine_variant="red standard",
            label_scope="regulated_gi",
            vine_density_per_ha=9000,
            irrigation_mm_per_week=0.0,
            planting_pattern="rows",
            row_spacing_m=1.25,
            vine_spacing_m=0.50,
            target_yield_t_ha=8.0,
            pruning_system="guyot_simple",
            retained_buds_per_vine=8,
            fruiting_shoots_per_vine=8,
            support_system="trellis",
            canopy_height_m=0.75,
            parcel_crop_load_kg_ha=9000.0,
            dead_missing_vine_fraction=0.50,
        )
        result = engine.simulate(block, self.weather(), vintage_year=2026)
        self.assertTrue(any("authorized yield" in warning for warning in result.warnings))
        if result.yield_hl_ha > 25.0:
            self.assertFalse(result.label_eligible)
            self.assertTrue(any("dead/missing-vine-adjusted" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
