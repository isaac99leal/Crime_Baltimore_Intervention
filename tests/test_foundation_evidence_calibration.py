from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sommelier_v2.knowledge.fermentation_guidance import (
    assess_alcoholic_fermentation,
    assess_malolactic_conditions,
    estimate_sparkling_co2_volumes,
    minimum_low_risk_yan_mg_l,
)
from sommelier_v2.knowledge.fermentation_process import FermentationPlan, MustComposition
from sommelier_v2.knowledge.legal_rules import LegalAwareRegionGrapeRulebook
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.site_sources import NamedSiteSourceRegistry
from sommelier_v2.knowledge.vintage_engine import DailyWeather
from sommelier_v2.knowledge.vintage_indices import calculate_vintage_climate_indices


class StrictLegalAuthorizationTests(unittest.TestCase):
    def test_legacy_allowed_grapes_cannot_positively_authorize_a_gi(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            regions = root / "regions.json"
            regions.write_text(
                json.dumps(
                    {
                        "regions": [
                            {
                                "country": "Testland",
                                "wine_regions": [
                                    {
                                        "name": "Legacy Valley",
                                        "primary_grapes": ["Merlot"],
                                        "sub_regions": [
                                            {
                                                "name": "Core",
                                                "primary_grapes": ["Merlot"],
                                                "communes": [
                                                    {
                                                        "name": "Legacy GI",
                                                        "primary_grapes": ["Merlot"],
                                                        "allowed_grapes": ["Merlot"],
                                                    }
                                                ],
                                            }
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            empty_specs_path = root / "empty_specs.json"
            empty_specs_path.write_text(
                json.dumps({"sources": {}, "specs": []}),
                encoding="utf-8",
            )
            rulebook = LegalAwareRegionGrapeRulebook(
                regions,
                legal_specs=LegalSpecRegistry(empty_specs_path),
            )

            decision = rulebook.evaluate(
                country="Testland",
                region="Legacy Valley",
                appellation="Legacy GI",
                grapes={"Merlot": 100},
                label_scope="regulated_gi",
            )

            self.assertFalse(decision.eligible)
            self.assertEqual(decision.status, "strict_legal_spec_pending")
            self.assertTrue(
                any("cannot certify" in warning for warning in decision.warnings)
            )


class VintageEvidenceIndexTests(unittest.TestCase):
    def test_transparent_indices_are_deterministic(self):
        days = [
            DailyWeather(
                day_of_year=day,
                tmin_c=20.0,
                tmax_c=30.0,
                rain_mm=1.5,
                humidity_pct=60.0,
                solar_mj_m2=20.0,
                wind_m_s=2.0,
            )
            for day in range(100, 110)
        ]
        indices = calculate_vintage_climate_indices(days, harvest_day=109)

        self.assertAlmostEqual(indices.growing_degree_days_c, 150.0)
        self.assertAlmostEqual(indices.huglin_heat_sum, 175.0)
        self.assertAlmostEqual(indices.growing_season_mean_temp_c, 25.0)
        self.assertAlmostEqual(indices.mean_diurnal_range_c, 10.0)
        self.assertAlmostEqual(indices.growing_season_rain_mm, 15.0)
        self.assertEqual(indices.hot_nights_20c, 10)
        self.assertEqual(indices.rain_days_1mm, 10)

    def test_interval_and_harvest_must_be_coherent(self):
        days = [DailyWeather(day_of_year=100, tmin_c=10.0, tmax_c=20.0)]
        with self.assertRaises(ValueError):
            calculate_vintage_climate_indices(days, harvest_day=99)


class FermentationEvidenceGuidanceTests(unittest.TestCase):
    @staticmethod
    def must(**changes):
        values = dict(
            volume_l=1000.0,
            sugar_g_l=220.0,
            yan_mg_l=180.0,
            ph=3.35,
            titratable_acidity_g_l=6.2,
            malic_acid_g_l=2.8,
            temp_c=20.0,
        )
        values.update(changes)
        return MustComposition(**values)

    def test_yan_guides_remain_style_specific_and_advisory(self):
        self.assertEqual(minimum_low_risk_yan_mg_l("red"), 100.0)
        self.assertEqual(minimum_low_risk_yan_mg_l("white"), 150.0)
        self.assertIsNone(minimum_low_risk_yan_mg_l("orange"))

        red = assess_alcoholic_fermentation(
            self.must(yan_mg_l=80.0),
            FermentationPlan(style="red"),
        )
        white = assess_alcoholic_fermentation(
            self.must(yan_mg_l=120.0),
            FermentationPlan(style="white"),
        )
        self.assertEqual(red.status, "elevated_risk")
        self.assertEqual(white.status, "elevated_risk")
        self.assertGreater(red.risk_score, 0.0)
        self.assertGreater(white.risk_score, 0.0)

    def test_mlf_checks_total_so2_temperature_ph_and_alcohol(self):
        plan = FermentationPlan(
            style="red",
            malolactic=True,
            mlf_start_temp_c=12.0,
        )
        assessment = assess_malolactic_conditions(
            self.must(ph=2.95),
            plan,
            estimated_alcohol_pct=16.2,
            total_so2_mg_l=45.0,
        )
        self.assertEqual(assessment.status, "elevated_risk")
        self.assertGreaterEqual(len(assessment.issues), 4)

    def test_tirage_planning_relation(self):
        self.assertAlmostEqual(estimate_sparkling_co2_volumes(24.0), 6.0)
        self.assertAlmostEqual(
            estimate_sparkling_co2_volumes(20.0, base_wine_co2_volumes=0.5),
            5.5,
        )


class NamedSiteSourceRegistryTests(unittest.TestCase):
    def test_bulk_source_counts_and_scope(self):
        registry = NamedSiteSourceRegistry()
        stats = registry.stats()
        self.assertGreaterEqual(stats["named_site_bulk_sources"], 5)

        burgundy = registry.get("bivb_bourgogne_maps_2025")
        self.assertIsNotNone(burgundy)
        self.assertEqual(burgundy.reported_named_units, 11541)
        self.assertEqual(burgundy.reported_parcels, 296663)
        self.assertFalse(burgundy.legal_claim_authority)

        vienna = registry.get("vienna_riedenkarte_2026")
        self.assertIsNotNone(vienna)
        self.assertEqual(vienna.reported_named_units, 140)


if __name__ == "__main__":
    unittest.main()
