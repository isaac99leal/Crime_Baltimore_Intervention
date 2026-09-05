from __future__ import annotations

import unittest

from sommelier_v2.domain import WineStyle
from sommelier_v2.generation import ConstrainedWineBuilder, WineBuildRequest
from sommelier_v2.knowledge.fermentation_process import FermentationPlan, MustComposition
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory
from sommelier_v2.knowledge.regional_rules import OriginConstraintError, OriginDecision
from sommelier_v2.knowledge.site_claims import SiteClaimRegistry
from sommelier_v2.knowledge.vintage_engine import DailyWeather


class SiteClaimRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()
        cls.registry = SiteClaimRegistry()

    @classmethod
    def site(cls, *, name: str, site_type: str, parent: str):
        for site in cls.factory.catalog.named_sites:
            if site.name == name and site.site_type == site_type and site.parent == parent:
                return site
        raise AssertionError(f"Missing site seed {name}/{site_type}/{parent}")

    @staticmethod
    def strict_decision(grape: str = "Nebbiolo") -> OriginDecision:
        return OriginDecision(
            eligible=True,
            status="appellation_eligible_sourced_spec",
            label_scope="regulated_gi",
            canonical_grapes=(grape,),
            rule_id="strict:test",
            evidence=("strict_test_evidence",),
        )

    def test_barolo_mga_has_explicit_positive_claim_rule(self):
        site = self.site(name="Cannubi", site_type="MGA", parent="Barolo DOCG")
        decision = self.registry.evaluate(
            site=site,
            origin_decision=self.strict_decision(),
            appellation="Barolo DOCG",
        )
        self.assertTrue(decision.eligible)
        self.assertEqual(decision.status, "site_claim_eligible_verified_rule")
        self.assertEqual(decision.rule_id, "siteclaim:it:barolo:mga")

    def test_chianti_classico_uga_requires_gran_selezione_variant(self):
        site = self.site(name="Panzano", site_type="UGA", parent="Chianti Classico DOCG")
        standard = self.registry.evaluate(
            site=site,
            origin_decision=self.strict_decision("Sangiovese"),
            appellation="Chianti Classico DOCG",
            wine_variant="standard",
        )
        gran_selezione = self.registry.evaluate(
            site=site,
            origin_decision=self.strict_decision("Sangiovese"),
            appellation="Chianti Classico DOCG",
            wine_variant="gran selezione",
        )
        self.assertFalse(standard.eligible)
        self.assertEqual(standard.status, "site_claim_rule_conditions_not_met")
        self.assertTrue(gran_selezione.eligible)

    def test_documented_burgundy_climat_is_not_auto_authorized_for_label_use(self):
        site = self.site(
            name="Les Amoureuses",
            site_type="climat",
            parent="Chambolle-Musigny",
        )
        decision = self.registry.evaluate(
            site=site,
            origin_decision=self.strict_decision("Pinot Noir"),
            appellation="Chambolle-Musigny",
        )
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.status, "site_claim_rule_unverified")

    def test_legacy_positive_origin_status_cannot_support_site_claim(self):
        site = self.site(name="Cannubi", site_type="MGA", parent="Barolo DOCG")
        legacy = OriginDecision(
            eligible=True,
            status="appellation_eligible",
            label_scope="regulated_gi",
            canonical_grapes=("Nebbiolo",),
            rule_id="legacy:test",
        )
        decision = self.registry.evaluate(
            site=site,
            origin_decision=legacy,
            appellation="Barolo DOCG",
        )
        self.assertFalse(decision.eligible)
        self.assertEqual(
            decision.status,
            "strict_parent_spec_required_for_site_claim",
        )


class OriginFactorySiteClaimIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()
        cls.cannubi = next(
            site
            for site in cls.factory.catalog.named_sites
            if site.name == "Cannubi"
            and site.site_type == "MGA"
            and site.parent == "Barolo DOCG"
        )
        cls.panzano = next(
            site
            for site in cls.factory.catalog.named_sites
            if site.name == "Panzano"
            and site.site_type == "UGA"
            and site.parent == "Chianti Classico DOCG"
        )

    def test_factory_keeps_parent_gi_and_site_claim_as_separate_gates(self):
        origin = self.factory.create(
            OriginRequest(
                country="Italy",
                region=self.cannubi.region,
                appellation="Barolo DOCG",
                grapes={"Nebbiolo": 100},
                vintage_year=2022,
                label_scope="regulated_gi",
                site_id=self.cannubi.id,
            )
        )
        self.assertTrue(origin.decision.eligible)
        self.assertTrue(origin.site_claim_eligible)
        self.assertEqual(origin.site_claim_rule_id, "siteclaim:it:barolo:mga")

    def test_factory_enforces_uga_variant_condition(self):
        standard = self.factory.create(
            OriginRequest(
                country="Italy",
                region=self.panzano.region,
                appellation="Chianti Classico DOCG",
                grapes={"Sangiovese": 100},
                vintage_year=2022,
                label_scope="regulated_gi",
                site_id=self.panzano.id,
                wine_variant="standard",
            )
        )
        gran_selezione = self.factory.create(
            OriginRequest(
                country="Italy",
                region=self.panzano.region,
                appellation="Chianti Classico DOCG",
                grapes={"Sangiovese": 100},
                vintage_year=2022,
                label_scope="regulated_gi",
                site_id=self.panzano.id,
                wine_variant="gran selezione",
            )
        )
        self.assertFalse(standard.site_claim_eligible)
        self.assertTrue(gran_selezione.site_claim_eligible)


class ConstrainedWineBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()
        cls.builder = ConstrainedWineBuilder(origin_factory=cls.factory)
        cls.cannubi = next(
            site
            for site in cls.factory.catalog.named_sites
            if site.name == "Cannubi"
            and site.site_type == "MGA"
            and site.parent == "Barolo DOCG"
        )

    def barolo_request(self, grape: str = "Nebbiolo") -> WineBuildRequest:
        return WineBuildRequest(
            id="generated:test:barolo",
            producer="Fictional Estate",
            label="Barolo",
            origin=OriginRequest(
                country="Italy",
                region=self.cannubi.region,
                appellation="Barolo DOCG",
                grapes={grape: 100},
                vintage_year=2022,
                label_scope="regulated_gi",
                site_id=self.cannubi.id,
            ),
            style=WineStyle.RED,
            alcohol=14.5,
            wholesale_cost=45.0,
            rarity=0.45,
        )

    def test_builder_emits_verified_site_name_and_canonical_origin(self):
        result = self.builder.build(self.barolo_request())
        self.assertEqual(result.wine.appellation, "Barolo DOCG")
        self.assertEqual(result.wine.grapes, ("Nebbiolo",))
        self.assertEqual(result.wine.vineyard, "Cannubi")
        self.assertTrue(result.evidence.site_claim_eligible)
        self.assertEqual(result.evidence.origin_status, "appellation_eligible_sourced_spec")

    def test_builder_rejects_impossible_barolo_grape_before_other_evidence(self):
        weather = [
            DailyWeather(day_of_year=day, tmin_c=15.0, tmax_c=28.0)
            for day in range(100, 110)
        ]
        with self.assertRaises(OriginConstraintError):
            self.builder.build(
                self.barolo_request("Sangiovese"),
                weather_days=weather,
                harvest_day=109,
            )

    def test_builder_attaches_vintage_and_fermentation_evidence(self):
        weather = [
            DailyWeather(
                day_of_year=day,
                tmin_c=15.0,
                tmax_c=28.0,
                rain_mm=1.0,
                humidity_pct=60.0,
                solar_mj_m2=20.0,
                wind_m_s=2.0,
            )
            for day in range(100, 110)
        ]
        must = MustComposition(
            volume_l=1000.0,
            sugar_g_l=235.0,
            yan_mg_l=120.0,
            ph=3.35,
            titratable_acidity_g_l=6.0,
            malic_acid_g_l=2.5,
            temp_c=22.0,
        )
        plan = FermentationPlan(style="red", malolactic=True, mlf_start_temp_c=20.0)

        result = self.builder.build(
            self.barolo_request(),
            weather_days=weather,
            harvest_day=109,
            must=must,
            fermentation_plan=plan,
            total_so2_mg_l=25.0,
        )
        self.assertIsNotNone(result.evidence.vintage_indices)
        self.assertIsNotNone(result.evidence.alcoholic_fermentation_guidance)
        self.assertIsNotNone(result.evidence.malolactic_guidance)

    def test_builder_rejects_cross_producer_identity(self):
        request = self.barolo_request()
        request = WineBuildRequest(
            id=request.id,
            producer="Commercial Producer B",
            label=request.label,
            origin=OriginRequest(
                country=request.origin.country,
                region=request.origin.region,
                appellation=request.origin.appellation,
                grapes=request.origin.grapes,
                vintage_year=request.origin.vintage_year,
                label_scope=request.origin.label_scope,
                site_id=request.origin.site_id,
                producer="Validated Producer A",
            ),
            style=request.style,
        )
        with self.assertRaises(ValueError):
            self.builder.build(request)


if __name__ == "__main__":
    unittest.main()
