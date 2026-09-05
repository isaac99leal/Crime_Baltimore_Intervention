from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

from sommelier_v2.catalog import constrain_legacy_record
from sommelier_v2.domain import WineRecord
from sommelier_v2.knowledge.expanded_catalog import NamedSite
from sommelier_v2.knowledge.fermentation_process import (
    FermentationConstraintError,
    FermentationPlan,
    MustComposition,
    NutrientAddition,
    run_fermentation,
)
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory
from sommelier_v2.knowledge.regional_rules import OriginConstraintError, RegionGrapeRulebook
from sommelier_v2.knowledge.vineyard_engine import VineyardBlock, VineyardEngine
from sommelier_v2.knowledge.vintage_engine import DailyWeather


@dataclass
class FakeGrape:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    phenology: object = field(default_factory=lambda: SimpleNamespace(
        budbreak_relative=0.0, flowering_relative=0.0, veraison_relative=0.0,
        harvest_relative=0.0, heat_requirement_index=0.5, heat_spike_sensitivity=0.5,
    ))
    viticulture: object = field(default_factory=lambda: SimpleNamespace(
        acidity_retention=0.6, drought_tolerance=0.5,
        botrytis_susceptibility=0.4, rot_susceptibility=0.4,
    ))


@dataclass(frozen=True)
class Area:
    prime_name: str
    country: str
    area_2023_ha: float | None = None
    area_2016_ha: float | None = None
    area_2010_ha: float | None = None
    area_2000_ha: float | None = None


class FakeCatalog:
    def __init__(self):
        self._grapes = [
            FakeGrape("g:allowed", "Allowed", ["Alias Allowed"]),
            FakeGrape("g:forbidden", "Forbidden"),
        ]
        self.commercial_observations = []
        self.named_sites = []

    @staticmethod
    def norm(value):
        return "".join(ch.lower() for ch in value if ch.isalnum())

    def grape(self, name):
        key = self.norm(name)
        for grape in self._grapes:
            names = {self.norm(grape.name)}
            names.update(self.norm(alias) for alias in grape.aliases)
            if key in names:
                return grape
        return None

    def area_for(self, name, country=None):
        grape = self.grape(name)
        if grape and grape.id == "g:allowed" and country == "Testland":
            return [Area("Allowed", "Testland", area_2023_ha=12.0)]
        return []


def write_regions(path: Path):
    path.write_text(json.dumps({"regions":[{
        "country":"Testland",
        "wine_regions":[{
            "name":"Strict Valley", "classification_system":"Test GI", "primary_grapes":["Allowed"],
            "sub_regions":[{"name":"Core", "primary_grapes":["Allowed"], "communes":[
                {"name":"Strict GI", "primary_grapes":["Allowed"], "allowed_grapes":["Allowed"], "max_yield_hl_ha":80, "min_alcohol":10.0, "required_aging_months":12},
                {"name":"Unknown-Law GI", "primary_grapes":["Allowed"], "allowed_grapes":[]}
            ]}]
        }]
    }]}), encoding="utf-8")


class OriginAndVineyardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / "regions.json"
        write_regions(path)
        self.catalog = FakeCatalog()
        self.rules = RegionGrapeRulebook(path, catalog=self.catalog)
        self.site = NamedSite(
            id="site:test:strict", name="Block One", country="Testland",
            region="Strict Valley", site_type="lieu_dit", parent="Strict GI",
            classification="Test classified site", legal_status="official_appellation_lieu_dit",
        )
        self.engine = VineyardEngine(catalog=self.catalog, rulebook=self.rules, sites=[self.site])

    def tearDown(self):
        self.tmp.cleanup()

    def test_allowed_alias_and_factory_gate(self):
        decision = self.rules.evaluate(
            country="Testland", region="Strict Valley", appellation="Strict GI",
            grapes={"Alias Allowed":100}, label_scope="regulated_gi")
        self.assertTrue(decision.eligible)
        factory = WineOriginFactory(catalog=self.catalog, rulebook=self.rules)
        good = factory.create(OriginRequest(
            country="Testland", region="Strict Valley", appellation="Strict GI",
            grapes={"Alias Allowed":100}, vintage_year=2026, label_scope="regulated_gi"))
        self.assertEqual(good.canonical_grapes, ("Allowed",))
        with self.assertRaises(OriginConstraintError):
            factory.create(OriginRequest(
                country="Testland", region="Strict Valley", appellation="Strict GI",
                grapes={"Forbidden":100}, vintage_year=2026, label_scope="regulated_gi"))

    def test_forbidden_and_unknown_law_are_blocked(self):
        forbidden = self.rules.evaluate(
            country="Testland", region="Strict Valley", appellation="Strict GI",
            grapes={"Forbidden":100}, label_scope="regulated_gi")
        self.assertFalse(forbidden.eligible)
        self.assertEqual(forbidden.status, "grape_not_permitted_for_appellation")
        unknown = self.rules.evaluate(
            country="Testland", region="Strict Valley", appellation="Unknown-Law GI",
            grapes={"Allowed":100}, label_scope="regulated_gi")
        self.assertFalse(unknown.eligible)
        self.assertEqual(unknown.status, "legal_grape_rule_unverified")

    def test_regional_style_uses_primary_grapes_but_is_not_legal(self):
        plausible = self.rules.evaluate(
            country="Testland", region="Strict Valley", appellation="Unknown-Law GI",
            grapes={"Alias Allowed":100}, label_scope="regional_style")
        self.assertTrue(plausible.eligible)
        self.assertEqual(plausible.status, "regional_style_supported")
        self.assertTrue(any("not a legal" in warning.lower() for warning in plausible.warnings))
        impossible = self.rules.evaluate(
            country="Testland", region="Strict Valley", appellation="Unknown-Law GI",
            grapes={"Forbidden":100}, label_scope="regional_style")
        self.assertFalse(impossible.eligible)
        self.assertEqual(impossible.status, "grape_not_plausible_for_region")

    def test_country_wine_requires_evidence_or_experimental(self):
        blocked = self.rules.evaluate(country="Testland", grapes={"Forbidden":100}, label_scope="country_wine")
        self.assertFalse(blocked.eligible)
        allowed = self.rules.evaluate(country="Testland", grapes={"Forbidden":100}, label_scope="experimental", experimental=True)
        self.assertTrue(allowed.eligible)

    def test_legacy_catalog_bridge_cannot_bypass_region_grape_gate(self):
        allowed_record = WineRecord(
            id="legacy-ok", producer="P", label="L",
            country="Testland", region="Strict Valley",
            subregion="Core", appellation="Unknown-Law GI",
            grapes=("Alias Allowed",),
        )
        accepted = constrain_legacy_record(allowed_record, self.rules)
        self.assertIsNotNone(accepted)
        self.assertEqual(accepted.grapes, ("Allowed",))
        impossible_record = WineRecord(
            id="legacy-bad", producer="P", label="L",
            country="Testland", region="Strict Valley",
            subregion="Core", appellation="Unknown-Law GI",
            grapes=("Forbidden",),
        )
        self.assertIsNone(constrain_legacy_record(impossible_record, self.rules))

    @staticmethod
    def weather():
        return [DailyWeather(
            day_of_year=doy, tmin_c=14.0, tmax_c=29.0,
            rain_mm=7.0 if doy % 10 == 0 else 0.3,
            humidity_pct=62.0, solar_mj_m2=20.0, wind_m_s=2.2)
            for doy in range(80, 311)]

    def test_vineyard_block_simulates_and_illegal_grape_cannot_claim_gi(self):
        good = VineyardBlock(
            id="b1", grape="Alias Allowed", area_ha=1.2, planting_year=2000,
            country="Testland", region="Strict Valley", appellation="Strict GI",
            site_id=self.site.id, label_scope="regulated_gi", target_yield_t_ha=6.0)
        result = self.engine.simulate(good, self.weather(), vintage_year=2026)
        self.assertTrue(result.origin_decision.eligible)
        self.assertGreater(result.brix, 0)
        self.assertGreater(result.total_grape_tonnes, 0)
        bad = VineyardBlock(
            id="b2", grape="Forbidden", area_ha=1.0, planting_year=2010,
            country="Testland", region="Strict Valley", appellation="Strict GI",
            site_id=self.site.id, label_scope="regulated_gi")
        with self.assertRaises(OriginConstraintError):
            self.engine.simulate(bad, self.weather(), vintage_year=2026)


class FermentationTests(unittest.TestCase):
    @staticmethod
    def must(**changes):
        values = dict(volume_l=1000.0, sugar_g_l=220.0, yan_mg_l=180.0, ph=3.45,
                      titratable_acidity_g_l=6.2, malic_acid_g_l=2.8, temp_c=21.0)
        values.update(changes)
        return MustComposition(**values)

    def test_dry_fermentation_mlf_and_mass_balance(self):
        must = self.must(yan_mg_l=300.0, temp_c=25.0)
        result = run_fermentation(must, FermentationPlan(
            style="red", target_residual_sugar_g_l=2.0, max_hours=1200.0,
            nutrient_additions=(NutrientAddition(hour=24, yan_mg_l=30),), malolactic=True))
        self.assertTrue(result.alcoholic_completed, f"status={result.status} sugar={result.final_sugar_g_l:.4f} ethanol={result.final_ethanol_pct:.4f} hours={result.alcoholic_history[-1].hour:.1f} stuck={result.stuck} risk={result.alcoholic_history[-1].stuck_risk:.4f}")
        self.assertTrue(result.dry)
        self.assertLessEqual(result.final_sugar_g_l, 2.1)
        self.assertLess(result.final_malic_acid_g_l, must.malic_acid_g_l)
        self.assertLessEqual(result.final_ethanol_pct, must.sugar_g_l / 16.83 + 1e-6)

    def test_sweet_wine_requires_and_obeys_arrest(self):
        with self.assertRaises(FermentationConstraintError):
            run_fermentation(self.must(), FermentationPlan(target_residual_sugar_g_l=35.0))
        result = run_fermentation(self.must(sugar_g_l=240.0), FermentationPlan(
            target_residual_sugar_g_l=35.0, arrest_method="chill_and_sterile_filter"))
        self.assertTrue(result.arrested)
        self.assertAlmostEqual(result.final_sugar_g_l, 35.0, places=5)

    def test_impossible_must_is_rejected(self):
        with self.assertRaises(FermentationConstraintError):
            run_fermentation(self.must(ph=6.5), FermentationPlan())


if __name__ == "__main__":
    unittest.main()
