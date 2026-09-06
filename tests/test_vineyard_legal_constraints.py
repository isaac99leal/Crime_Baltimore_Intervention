from __future__ import annotations

import unittest

from sommelier_v2.knowledge import VineyardBlock, VineyardEngine
from sommelier_v2.knowledge.vineyard_legal_constraints import VineyardLegalConstraintRegistry
from sommelier_v2.knowledge.vintage_engine import DailyWeather


class VineyardLegalConstraintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = VineyardLegalConstraintRegistry()

    @staticmethod
    def valid_geometry() -> dict[str, object]:
        return {
            "planting_pattern": "rows",
            "row_spacing_m": 1.25,
            "vine_spacing_m": 0.50,
        }

    def test_fixin_and_vougeot_constraints_resolve(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            row = self.registry.resolve(country="France", appellation=appellation)
            self.assertIsNotNone(row)
            self.assertEqual(row.min_vine_density_per_ha, 9000)
            self.assertIs(row.irrigation_prohibited, True)
            self.assertEqual(row.allowed_planting_patterns, ("rows", "foule"))
            self.assertEqual(row.max_row_spacing_m, 1.25)
            self.assertEqual(row.min_vine_spacing_m, 0.50)
            self.assertTrue(row.source_ids)

    def test_density_boundary_is_exact(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            good = self.registry.assess(
                country="France",
                appellation=appellation,
                vine_density_per_ha=9000,
                irrigation_mm_per_week=0.0,
                **self.valid_geometry(),
            )
            bad = self.registry.assess(
                country="France",
                appellation=appellation,
                vine_density_per_ha=8999,
                irrigation_mm_per_week=0.0,
                **self.valid_geometry(),
            )
            self.assertIs(good.satisfied, True)
            self.assertEqual(good.status, "reviewed_vineyard_constraints_satisfied")
            self.assertIs(bad.satisfied, False)
            self.assertEqual(bad.status, "reviewed_vineyard_constraint_violation")
            self.assertTrue(any("9,000" in issue for issue in bad.issues))

    def test_any_positive_irrigation_violates_reviewed_rule(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            dry = self.registry.assess(
                country="France",
                appellation=appellation,
                vine_density_per_ha=9000,
                irrigation_mm_per_week=0.0,
                **self.valid_geometry(),
            )
            irrigated = self.registry.assess(
                country="France",
                appellation=appellation,
                vine_density_per_ha=9000,
                irrigation_mm_per_week=0.01,
                **self.valid_geometry(),
            )
            self.assertIs(dry.satisfied, True)
            self.assertIs(irrigated.satisfied, False)
            self.assertTrue(any("Irrigation is prohibited" in issue for issue in irrigated.issues))

    def test_row_and_vine_spacing_boundaries_are_exact(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            exact = self.registry.assess(
                country="France",
                appellation=appellation,
                vine_density_per_ha=9000,
                irrigation_mm_per_week=0.0,
                planting_pattern="rows",
                row_spacing_m=1.25,
                vine_spacing_m=0.50,
            )
            wide_rows = self.registry.assess(
                country="France",
                appellation=appellation,
                vine_density_per_ha=9000,
                irrigation_mm_per_week=0.0,
                planting_pattern="rows",
                row_spacing_m=1.251,
                vine_spacing_m=0.50,
            )
            tight_vines = self.registry.assess(
                country="France",
                appellation=appellation,
                vine_density_per_ha=9000,
                irrigation_mm_per_week=0.0,
                planting_pattern="rows",
                row_spacing_m=1.25,
                vine_spacing_m=0.499,
            )
            self.assertIs(exact.satisfied, True)
            self.assertIs(wide_rows.satisfied, False)
            self.assertTrue(any("Row spacing" in issue for issue in wide_rows.issues))
            self.assertIs(tight_vines.satisfied, False)
            self.assertTrue(any("Vine spacing" in issue for issue in tight_vines.issues))

    def test_foule_is_not_forced_into_row_geometry(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            good = self.registry.assess(
                country="France",
                appellation=appellation,
                vine_density_per_ha=9000,
                irrigation_mm_per_week=0.0,
                planting_pattern="foule",
                row_spacing_m=None,
                vine_spacing_m=0.50,
            )
            too_tight = self.registry.assess(
                country="France",
                appellation=appellation,
                vine_density_per_ha=9000,
                irrigation_mm_per_week=0.0,
                planting_pattern="foule",
                row_spacing_m=None,
                vine_spacing_m=0.49,
            )
            self.assertIs(good.satisfied, True)
            self.assertIs(too_tight.satisfied, False)
            self.assertFalse(any("Row spacing" in warning for warning in good.warnings))

    def test_missing_geometry_is_unknown_not_assumed(self) -> None:
        decision = self.registry.assess(
            country="France",
            appellation="Fixin",
            vine_density_per_ha=9000,
            irrigation_mm_per_week=0.0,
            planting_pattern=None,
            row_spacing_m=None,
            vine_spacing_m=None,
        )
        self.assertIsNone(decision.satisfied)
        self.assertEqual(decision.status, "reviewed_vineyard_constraint_unobserved")
        self.assertTrue(any("Planting pattern" in warning for warning in decision.warnings))
        self.assertTrue(any("Vine-to-vine spacing" in warning for warning in decision.warnings))

    def test_missing_irrigation_measurement_is_unknown(self) -> None:
        decision = self.registry.assess(
            country="France",
            appellation="Fixin",
            vine_density_per_ha=9000,
            irrigation_mm_per_week=None,
            **self.valid_geometry(),
        )
        self.assertIsNone(decision.satisfied)
        self.assertEqual(decision.status, "reviewed_vineyard_constraint_unobserved")

    def test_unreviewed_origin_is_unknown_not_permission(self) -> None:
        decision = self.registry.assess(
            country="France",
            appellation="Imaginary-Unreviewed-Origin",
            vine_density_per_ha=10000,
            irrigation_mm_per_week=0.0,
            **self.valid_geometry(),
        )
        self.assertIsNone(decision.satisfied)
        self.assertEqual(decision.status, "vineyard_law_not_reviewed")

    def test_default_legal_engine_uses_enriched_site_registry(self) -> None:
        engine = VineyardEngine()
        self.assertIn("site:germany:rlp:einzellage:110140", engine.site_registry.by_id)

    def test_foule_cannot_claim_a_row_spacing_measurement(self) -> None:
        engine = VineyardEngine()
        block = VineyardBlock(
            id="invalid-foule-geometry",
            grape="Pinot Noir",
            area_ha=1.0,
            planting_year=2000,
            country="France",
            region="Bourgogne",
            planting_pattern="foule",
            row_spacing_m=1.0,
            vine_spacing_m=0.50,
        )
        with self.assertRaisesRegex(ValueError, "not applicable"):
            engine.validate_block(block, vintage_year=2026)

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

    def test_under_density_fixin_remains_physical_but_is_declassified(self) -> None:
        engine = VineyardEngine()
        block = VineyardBlock(
            id="fixin-under-density",
            grape="Pinot Noir",
            area_ha=1.0,
            planting_year=2000,
            country="France",
            region="Bourgogne",
            appellation="Fixin",
            wine_variant="red standard",
            label_scope="regulated_gi",
            vine_density_per_ha=8999,
            irrigation_mm_per_week=0.0,
            planting_pattern="rows",
            row_spacing_m=1.25,
            vine_spacing_m=0.50,
            target_yield_t_ha=4.0,
        )
        result = engine.simulate(block, self.weather(), vintage_year=2026)
        self.assertTrue(result.harvestable)
        self.assertFalse(result.label_eligible)
        self.assertTrue(any("below the sourced Fixin minimum" in issue for issue in result.issues))

    def test_irrigated_vougeot_remains_physical_but_is_declassified(self) -> None:
        engine = VineyardEngine()
        block = VineyardBlock(
            id="vougeot-irrigated",
            grape="Pinot Noir",
            area_ha=1.0,
            planting_year=2000,
            country="France",
            region="Bourgogne",
            appellation="Vougeot",
            wine_variant="red standard",
            label_scope="regulated_gi",
            vine_density_per_ha=9000,
            irrigation_mm_per_week=1.0,
            irrigation_allowed=True,
            planting_pattern="rows",
            row_spacing_m=1.25,
            vine_spacing_m=0.50,
            target_yield_t_ha=4.0,
        )
        result = engine.simulate(block, self.weather(), vintage_year=2026)
        self.assertTrue(result.harvestable)
        self.assertFalse(result.label_eligible)
        self.assertTrue(any("Irrigation is prohibited" in issue for issue in result.issues))

    def test_wide_rows_remain_physical_but_declassify_fixin(self) -> None:
        engine = VineyardEngine()
        block = VineyardBlock(
            id="fixin-wide-rows",
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
            row_spacing_m=1.30,
            vine_spacing_m=0.50,
            target_yield_t_ha=4.0,
        )
        result = engine.simulate(block, self.weather(), vintage_year=2026)
        self.assertTrue(result.harvestable)
        self.assertFalse(result.label_eligible)
        self.assertTrue(any("Row spacing" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
