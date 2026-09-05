from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.domain import WineStyle
from sommelier_v2.generation import ConstrainedWineBuilder, WineBuildRequest
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory
from sommelier_v2.knowledge.site_claims import SiteClaimRegistry


class Chablis2025LegalSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_current_standard_and_premier_cru_specs_resolve(self):
        standard = self.registry.resolve(
            country="France", appellation="Chablis", variant="standard"
        )
        premier = self.registry.resolve(
            country="France", appellation="Chablis", variant="premier cru"
        )
        self.assertIsNotNone(standard)
        self.assertIsNotNone(premier)
        self.assertEqual(standard.id, "fr:chablis:standard")
        self.assertEqual(premier.id, "fr:chablis:premier-cru")
        self.assertEqual(standard.effective_from, "2025-09-12")
        self.assertEqual(premier.effective_from, "2025-09-12")

    def test_current_machine_limits_are_level_specific(self):
        standard = self.registry.resolve(
            country="France", appellation="Chablis", variant="standard"
        )
        premier = self.registry.resolve(
            country="France", appellation="Chablis", variant="premier cru"
        )
        self.assertIsNotNone(standard)
        self.assertIsNotNone(premier)

        self.assertEqual(standard.allowed_grapes, ("Chardonnay",))
        self.assertEqual(standard.min_must_sugar_g_l, 161.0)
        self.assertEqual(standard.min_potential_alcohol_pct, 10.0)
        self.assertEqual(standard.max_yield_hl_ha, 60.0)
        self.assertEqual(standard.max_total_alcohol_pct, 13.0)
        self.assertEqual(standard.max_residual_sugar_g_l, 3.0)

        self.assertEqual(premier.allowed_grapes, ("Chardonnay",))
        self.assertEqual(premier.min_must_sugar_g_l, 170.0)
        self.assertEqual(premier.min_potential_alcohol_pct, 10.5)
        self.assertEqual(premier.max_yield_hl_ha, 58.0)
        self.assertEqual(premier.max_total_alcohol_pct, 13.5)
        self.assertEqual(premier.max_residual_sugar_g_l, 3.0)

    def test_no_chablis_grand_cru_release_calendar_is_invented(self):
        for variant in ("standard", "premier cru"):
            spec = self.registry.resolve(
                country="France", appellation="Chablis", variant=variant
            )
            self.assertIsNotNone(spec)
            self.assertIsNone(spec.min_elevage_year_offset)
            self.assertIsNone(spec.min_elevage_until_month)
            self.assertIsNone(spec.min_elevage_until_day)
            self.assertIsNone(spec.release_year_offset)
            self.assertIsNone(spec.earliest_release_month)
            self.assertIsNone(spec.earliest_release_day)

    def test_premier_cru_production_and_release_limits_fail_closed(self):
        spec = self.registry.resolve(
            country="France", appellation="Chablis", variant="premier cru"
        )
        self.assertIsNotNone(spec)
        self.assertTrue(
            self.registry.validate_production(
                spec,
                wine_yield_hl_ha=58.0,
                must_sugar_g_l=170.0,
                potential_alcohol_pct=10.5,
                require_complete=True,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                spec,
                wine_yield_hl_ha=58.1,
                must_sugar_g_l=170.0,
                potential_alcohol_pct=10.5,
                require_complete=True,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                spec,
                wine_yield_hl_ha=58.0,
                must_sugar_g_l=169.9,
                potential_alcohol_pct=10.5,
                require_complete=True,
            ).eligible
        )
        self.assertTrue(
            self.registry.validate_release(
                spec,
                total_aging_months=0,
                total_alcohol_pct=13.5,
                residual_sugar_g_l=3.0,
                vintage_year=2025,
                require_complete=True,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_release(
                spec,
                total_aging_months=0,
                total_alcohol_pct=13.51,
                residual_sugar_g_l=3.0,
                vintage_year=2025,
                require_complete=True,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_release(
                spec,
                total_aging_months=0,
                total_alcohol_pct=13.5,
                residual_sugar_g_l=3.01,
                vintage_year=2025,
                require_complete=True,
            ).eligible
        )


class ChablisPremierCruSiteIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = WorldWineKnowledgeCatalog()
        cls.sites = [
            site
            for site in cls.catalog.named_sites
            if site.parent == "Chablis"
            and site.site_type == "climat"
            and site.classification == "Premier Cru"
        ]

    def test_current_spec_loads_exactly_40_premier_cru_climats(self):
        self.assertEqual(len(self.sites), 40)
        names = {site.name for site in self.sites}
        self.assertIn("Chapelot", names)
        self.assertIn("Montée de Tonnerre", names)
        self.assertIn("Fourchaume", names)
        self.assertIn("Vaulorent", names)
        self.assertIn("Butteaux", names)
        self.assertIn("Vaugiraut", names)
        self.assertEqual(
            {site.legal_status for site in self.sites},
            {"official_appellation_climat"},
        )

    def test_cover_group_registry_contains_17_principal_names(self):
        rule = next(
            rule
            for rule in SiteClaimRegistry().rules
            if rule.id == "siteclaim:fr:chablis:premier-cru-climat"
        )
        self.assertEqual(len(rule.cover_name_groups), 17)
        groups = {claim: set(physical) for claim, physical in rule.cover_name_groups}
        self.assertEqual(
            groups["Montée de Tonnerre"],
            {"Montée de Tonnerre", "Chapelot", "Côte de Bréchain", "Pied d'Aloup"},
        )
        self.assertEqual(
            groups["Fourchaume"],
            {"Fourchaume", "Côte de Fontenay", "L'Homme Mort", "Vaulorent", "Vaupulent"},
        )
        self.assertEqual(groups["Vosgros"], {"Vosgros", "Vaugiraut"})


class ChablisCoverClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = WorldWineKnowledgeCatalog()
        cls.factory = WineOriginFactory(catalog=cls.catalog)
        cls.builder = ConstrainedWineBuilder(origin_factory=cls.factory)
        cls.chapelot = next(
            site
            for site in cls.catalog.named_sites
            if site.parent == "Chablis"
            and site.name == "Chapelot"
            and site.site_type == "climat"
        )
        cls.butteaux = next(
            site
            for site in cls.catalog.named_sites
            if site.parent == "Chablis"
            and site.name == "Butteaux"
            and site.site_type == "climat"
        )
        cls.vaugiraut = next(
            site
            for site in cls.catalog.named_sites
            if site.parent == "Chablis"
            and site.name == "Vaugiraut"
            and site.site_type == "climat"
        )

    @staticmethod
    def _origin(site_id: str, claimed_site_name: str | None = None) -> OriginRequest:
        return OriginRequest(
            country="France",
            region="Chablis",
            appellation="Chablis",
            grapes={"Chardonnay": 100.0},
            vintage_year=2025,
            label_scope="regulated_gi",
            site_id=site_id,
            claimed_site_name=claimed_site_name,
            wine_variant="premier cru",
            producer="Test Producer",
        )

    def test_exact_physical_site_claim_remains_legal_without_new_argument(self):
        origin = self.factory.create(self._origin(self.chapelot.id))
        self.assertTrue(origin.site_claim_eligible)
        self.assertEqual(origin.site.name, "Chapelot")
        self.assertEqual(origin.site_claim_name, "Chapelot")

    def test_authorized_cover_name_preserves_physical_provenance(self):
        origin = self.factory.create(
            self._origin(self.chapelot.id, "Montée de Tonnerre")
        )
        self.assertTrue(origin.site_claim_eligible)
        self.assertEqual(origin.site.name, "Chapelot")
        self.assertEqual(origin.site_claim_name, "Montée de Tonnerre")
        self.assertIn("physical_site:Chapelot", origin.site_claim_evidence)
        self.assertIn(
            "authorized_cover_claim:Montée de Tonnerre",
            origin.site_claim_evidence,
        )

    def test_other_authorized_group_cover_names_work(self):
        butteaux = self.factory.create(self._origin(self.butteaux.id, "Montmains"))
        vaugiraut = self.factory.create(self._origin(self.vaugiraut.id, "Vosgros"))
        self.assertTrue(butteaux.site_claim_eligible)
        self.assertEqual(butteaux.site_claim_name, "Montmains")
        self.assertTrue(vaugiraut.site_claim_eligible)
        self.assertEqual(vaugiraut.site_claim_name, "Vosgros")

    def test_cross_group_cover_name_fails_closed(self):
        origin = self.factory.create(self._origin(self.chapelot.id, "Fourchaume"))
        self.assertFalse(origin.site_claim_eligible)
        self.assertEqual(origin.site.name, "Chapelot")
        self.assertEqual(origin.site_claim_name, "Fourchaume")
        self.assertEqual(origin.site_claim_status, "site_claim_rule_conditions_not_met")

    def test_generated_wine_uses_legal_claim_name_but_evidence_keeps_physical_site(self):
        request = WineBuildRequest(
            id="test:chablis:chapelot-as-montee-de-tonnerre",
            producer="Test Producer",
            label="Chablis Premier Cru Montée de Tonnerre",
            origin=self._origin(self.chapelot.id, "Montée de Tonnerre"),
            style=WineStyle.WHITE,
            classification="premier cru",
            wine_yield_hl_ha=52.0,
            must_sugar_g_l=171.0,
            potential_alcohol_pct=11.0,
            total_aging_months=0,
            total_alcohol_pct=13.0,
            residual_sugar_g_l=2.0,
            alcohol=12.5,
        )
        generated = self.builder.build(request)
        self.assertEqual(generated.wine.vineyard, "Montée de Tonnerre")
        self.assertEqual(generated.evidence.physical_site_name, "Chapelot")
        self.assertEqual(generated.evidence.site_claim_name, "Montée de Tonnerre")
        self.assertTrue(generated.evidence.site_claim_eligible)

    def test_invalid_cover_name_never_enters_game_facing_vineyard_field(self):
        request = WineBuildRequest(
            id="test:chablis:invalid-cover",
            producer="Test Producer",
            label="Chablis Premier Cru invalid cover",
            origin=self._origin(self.chapelot.id, "Fourchaume"),
            style=WineStyle.WHITE,
            classification="premier cru",
            wine_yield_hl_ha=52.0,
            must_sugar_g_l=171.0,
            potential_alcohol_pct=11.0,
            total_aging_months=0,
            total_alcohol_pct=13.0,
            residual_sugar_g_l=2.0,
            alcohol=12.5,
        )
        generated = self.builder.build(request)
        self.assertEqual(generated.wine.vineyard, "")
        self.assertEqual(generated.evidence.physical_site_name, "Chapelot")
        self.assertEqual(generated.evidence.site_claim_name, "Fourchaume")
        self.assertFalse(generated.evidence.site_claim_eligible)


class Chablis2025AuthoritativeCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = AuthoritativeCatalogGenerator().generate(
            as_of_year=2026,
            include_site_claims=True,
        )
        cls.rows = [item for item in cls.items if item.wine.appellation == "Chablis"]

    def test_default_market_has_one_standard_and_41_premier_cru_records(self):
        standard = [
            item for item in self.rows if item.legal_spec_id == "fr:chablis:standard"
        ]
        premier = [
            item for item in self.rows if item.legal_spec_id == "fr:chablis:premier-cru"
        ]
        self.assertEqual(len(standard), 1)
        self.assertEqual(len(premier), 41)
        self.assertEqual(len(self.rows), 42)
        self.assertEqual(standard[0].wine.vineyard, "")

    def test_default_market_keeps_exact_physical_climat_names_without_cover_duplicates(self):
        premier = [
            item for item in self.rows if item.legal_spec_id == "fr:chablis:premier-cru"
        ]
        site_rows = [item for item in premier if item.wine.vineyard]
        self.assertEqual(len(site_rows), 40)
        self.assertEqual(len({item.wine.vineyard for item in site_rows}), 40)
        self.assertIn("Chapelot", {item.wine.vineyard for item in site_rows})
        self.assertIn("Montée de Tonnerre", {item.wine.vineyard for item in site_rows})

    def test_chablis_grand_cru_remains_a_separate_protected_origin(self):
        self.assertFalse(
            any(item.wine.appellation == "Chablis grand cru" for item in self.rows)
        )
        grand_cru = [
            item
            for item in self.items
            if item.wine.appellation.casefold() == "chablis grand cru"
        ]
        self.assertTrue(grand_cru)
        self.assertTrue(all(item.legal_spec_id != "fr:chablis:premier-cru" for item in grand_cru))


if __name__ == "__main__":
    unittest.main()
