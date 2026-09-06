from __future__ import annotations

import unittest

from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


class FixinVougeotLegalMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = LegalSpecRegistry()

    def spec(self, appellation: str, variant: str):
        row = self.registry.resolve(country="France", appellation=appellation, variant=variant)
        self.assertIsNotNone(row)
        return row

    def test_exact_eight_variants_exist(self) -> None:
        rows = [
            spec
            for spec in self.registry.specs
            if spec.country == "France" and spec.appellation in {"Fixin", "Vougeot"}
        ]
        self.assertEqual(len(rows), 8)
        self.assertEqual(
            {(row.appellation, row.variant) for row in rows},
            {
                (appellation, variant)
                for appellation in ("Fixin", "Vougeot")
                for variant in (
                    "white standard",
                    "red standard",
                    "white premier cru",
                    "red premier cru",
                )
            },
        )

    def test_fixin_maturity_and_yield_matrix(self) -> None:
        expected = {
            "white standard": (178, 11.0, 57.0, 13.5),
            "red standard": (180, 10.5, 50.0, 13.5),
            "white premier cru": (187, 11.5, 55.0, 14.0),
            "red premier cru": (189, 11.0, 48.0, 14.0),
        }
        for variant, values in expected.items():
            spec = self.spec("Fixin", variant)
            self.assertEqual(
                (
                    spec.min_must_sugar_g_l,
                    spec.min_potential_alcohol_pct,
                    spec.max_yield_hl_ha,
                    spec.max_total_alcohol_pct,
                ),
                values,
            )

    def test_vougeot_maturity_and_yield_matrix(self) -> None:
        expected = {
            "white standard": (178, 11.0, 57.0, 13.5),
            "red standard": (180, 10.5, 50.0, 13.5),
            "white premier cru": (187, 11.5, 55.0, 14.0),
            "red premier cru": (189, 11.0, 48.0, 14.0),
        }
        for variant, values in expected.items():
            spec = self.spec("Vougeot", variant)
            self.assertEqual(
                (
                    spec.min_must_sugar_g_l,
                    spec.min_potential_alcohol_pct,
                    spec.max_yield_hl_ha,
                    spec.max_total_alcohol_pct,
                ),
                values,
            )

    def test_white_and_red_analytical_matrix(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            for variant in ("white standard", "white premier cru"):
                spec = self.spec(appellation, variant)
                self.assertEqual(spec.max_residual_sugar_g_l, 3.0)
                self.assertIsNone(spec.max_malic_acid_g_l)
            for variant in ("red standard", "red premier cru"):
                spec = self.spec(appellation, variant)
                self.assertEqual(spec.max_residual_sugar_g_l, 2.0)
                self.assertEqual(spec.max_malic_acid_g_l, 0.4)

    def test_exact_elevage_and_release_calendar(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            for variant in (
                "white standard",
                "red standard",
                "white premier cru",
                "red premier cru",
            ):
                spec = self.spec(appellation, variant)
                self.assertEqual(
                    (
                        spec.min_elevage_year_offset,
                        spec.min_elevage_until_month,
                        spec.min_elevage_until_day,
                    ),
                    (1, 6, 15),
                )
                self.assertEqual(
                    (
                        spec.release_year_offset,
                        spec.earliest_release_month,
                        spec.earliest_release_day,
                    ),
                    (1, 6, 30),
                )

    def test_fixin_white_does_not_invent_a_principal_grape_ratio(self) -> None:
        spec = self.spec("Fixin", "white premier cru")
        self.assertEqual(set(spec.allowed_grapes), {"Chardonnay", "Pinot Blanc"})
        self.assertTrue(self.registry.evaluate_blend(spec, "Chardonnay").eligible)
        self.assertTrue(self.registry.evaluate_blend(spec, "Pinot Blanc").eligible)

    def test_vougeot_white_pinot_blanc_cap_is_executable(self) -> None:
        spec = self.spec("Vougeot", "white premier cru")
        good = self.registry.evaluate_blend(spec, {"Chardonnay": 70, "Pinot Blanc": 30})
        bad = self.registry.evaluate_blend(spec, {"Chardonnay": 69, "Pinot Blanc": 31})
        self.assertTrue(good.eligible)
        self.assertFalse(bad.eligible)
        self.assertEqual(bad.status, "blend_percentage_violation")

    def test_red_accessory_grapes_do_not_become_cellar_blend_options(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            spec = self.spec(appellation, "red premier cru")
            self.assertTrue(self.registry.evaluate_blend(spec, "Pinot Noir").eligible)
            for accessory in ("Chardonnay", "Pinot Blanc", "Pinot Gris"):
                result = self.registry.evaluate_blend(
                    spec,
                    {"Pinot Noir": 95, accessory: 5},
                )
                self.assertFalse(result.eligible)
                self.assertEqual(result.status, "grape_not_permitted_for_appellation")

    def test_production_limits_execute(self) -> None:
        spec = self.spec("Fixin", "red premier cru")
        self.assertTrue(
            self.registry.validate_production(
                spec,
                wine_yield_hl_ha=48,
                must_sugar_g_l=189,
                potential_alcohol_pct=11.0,
                require_complete=True,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                spec,
                wine_yield_hl_ha=48.01,
                must_sugar_g_l=189,
                potential_alcohol_pct=11.0,
                require_complete=True,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                spec,
                wine_yield_hl_ha=48,
                must_sugar_g_l=188.9,
                potential_alcohol_pct=11.0,
                require_complete=True,
            ).eligible
        )

    def test_release_boundaries_execute(self) -> None:
        spec = self.spec("Vougeot", "red premier cru")
        good = self.registry.validate_release(
            spec,
            total_aging_months=9,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=2.0,
            malic_acid_g_l=0.4,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2026,
            release_month=6,
            release_day=30,
            require_complete=True,
        )
        too_early = self.registry.validate_release(
            spec,
            total_aging_months=9,
            total_alcohol_pct=14.0,
            residual_sugar_g_l=2.0,
            malic_acid_g_l=0.4,
            vintage_year=2025,
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=14,
            release_year=2026,
            release_month=6,
            release_day=29,
            require_complete=True,
        )
        self.assertTrue(good.eligible)
        self.assertFalse(too_early.eligible)

    def test_conditional_white_sugar_exception_is_not_generalized(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            spec = self.spec(appellation, "white standard")
            self.assertEqual(spec.max_residual_sugar_g_l, 3.0)
            decision = self.registry.validate_release(
                spec,
                total_aging_months=9,
                total_alcohol_pct=13.5,
                residual_sugar_g_l=3.1,
                vintage_year=2025,
                elevage_end_year=2026,
                elevage_end_month=6,
                elevage_end_day=15,
                release_year=2026,
                release_month=6,
                release_day=30,
                require_complete=True,
            )
            self.assertFalse(decision.eligible)


if __name__ == "__main__":
    unittest.main()
