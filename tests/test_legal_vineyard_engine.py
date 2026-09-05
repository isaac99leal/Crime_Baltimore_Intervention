from __future__ import annotations

import unittest

from sommelier_v2.knowledge import LegalVineyardEngine, VineyardBlock, VineyardEngine
from sommelier_v2.knowledge.regional_rules import OriginConstraintError
from sommelier_v2.knowledge.vintage_engine import DailyWeather


class LegalVineyardEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = VineyardEngine()

    def test_public_vineyard_engine_is_legal_aware(self):
        self.assertIsInstance(self.engine, LegalVineyardEngine)

    def test_real_brunello_grape_rule_is_enforced_at_block_validation(self):
        good = VineyardBlock(
            id="brunello-sangiovese", grape="Sangiovese", area_ha=1.0,
            planting_year=2000, country="Italy", region="Tuscany",
            appellation="Brunello di Montalcino DOCG", label_scope="regulated_gi",
        )
        _, decision = self.engine.validate_block(good, vintage_year=2026)
        self.assertTrue(decision.eligible)
        self.assertTrue(decision.rule_id.startswith("it:brunello"))

        bad = VineyardBlock(
            id="impossible-brunello", grape="Merlot", area_ha=1.0,
            planting_year=2000, country="Italy", region="Tuscany",
            appellation="Brunello di Montalcino DOCG", label_scope="regulated_gi",
        )
        with self.assertRaises(OriginConstraintError):
            self.engine.validate_block(bad, vintage_year=2026)

    @staticmethod
    def weather():
        return [
            DailyWeather(
                day_of_year=doy, tmin_c=15.0, tmax_c=30.0,
                rain_mm=5.0 if doy % 11 == 0 else 0.4,
                humidity_pct=58.0, solar_mj_m2=21.0, wind_m_s=2.0,
            )
            for doy in range(80, 311)
        ]

    def test_sourced_brunello_yield_limit_can_declassify_block(self):
        block = VineyardBlock(
            id="brunello-overcrop", grape="Sangiovese", area_ha=1.0,
            planting_year=1995, country="Italy", region="Tuscany",
            appellation="Brunello di Montalcino DOCG", label_scope="regulated_gi",
            target_yield_t_ha=30.0, crop_load_index=1.3,
        )
        result = self.engine.simulate(block, self.weather(), vintage_year=2026)
        self.assertGreater(result.yield_t_ha, 8.0)
        self.assertFalse(result.label_eligible)
        self.assertTrue(any("8.00 t/ha" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
