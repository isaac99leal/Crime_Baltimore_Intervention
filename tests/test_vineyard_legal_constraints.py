from __future__ import annotations

import unittest

from sommelier_v2.knowledge import VineyardBlock, VineyardEngine
from sommelier_v2.knowledge.vineyard_legal_constraints import VineyardLegalConstraintRegistry
from sommelier_v2.knowledge.vintage_engine import DailyWeather


class VineyardLegalConstraintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = VineyardLegalConstraintRegistry()

    def test_fixin_and_vougeot_density_constraints_resolve(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            row = self.registry.resolve(country="France", appellation=appellation)
            self.assertIsNotNone(row)
            self.assertEqual(row.min_vine_density_per_ha, 9000)
            self.assertTrue(row.source_ids)

    def test_density_boundary_is_exact(self) -> None:
        for appellation in ("Fixin", "Vougeot"):
            good = self.registry.assess(
                country="France",
                appellation=appellation,
                vine_density_per_ha=9000,
            )
            bad = self.registry.assess(
                country="France",
                appellation=appellation,
                vine_density_per_ha=8999,
            )
            self.assertIs(good.satisfied, True)
            self.assertEqual(good.status, "reviewed_vineyard_constraints_satisfied")
            self.assertIs(bad.satisfied, False)
            self.assertEqual(bad.status, "vine_density_below_legal_minimum")
            self.assertTrue(any("9,000" in issue for issue in bad.issues))

    def test_unreviewed_origin_is_unknown_not_permission(self) -> None:
        decision = self.registry.assess(
            country="France",
            appellation="Imaginary-Unreviewed-Origin",
            vine_density_per_ha=10000,
        )
        self.assertIsNone(decision.satisfied)
        self.assertEqual(decision.status, "vineyard_law_not_reviewed")

    def test_default_legal_engine_uses_enriched_site_registry(self) -> None:
        engine = VineyardEngine()
        self.assertIn("site:germany:rlp:einzellage:110140", engine.site_registry.by_id)

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
            target_yield_t_ha=4.0,
        )
        result = engine.simulate(block, self.weather(), vintage_year=2026)
        self.assertTrue(result.harvestable)
        self.assertFalse(result.label_eligible)
        self.assertTrue(any("below the sourced Fixin minimum" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
