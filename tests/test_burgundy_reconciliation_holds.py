from __future__ import annotations

import unittest

from sommelier_v2.knowledge import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory
from sommelier_v2.knowledge.site_claims import SiteClaimRegistry


class BurgundyPendingClaimHoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = WorldWineKnowledgeCatalog()
        cls.factory = WineOriginFactory(catalog=cls.catalog)
        cls.claims = SiteClaimRegistry()

    def marsannay_site(self, name: str):
        return next(
            site
            for site in self.catalog.named_sites
            if site.parent == "Marsannay" and site.name == name
        )

    def marsannay_origin(self, site_name: str, variant: str, grape: str):
        site = self.marsannay_site(site_name)
        return self.factory.create(
            OriginRequest(
                country="France",
                region="Bourgogne",
                appellation="Marsannay",
                grapes={grape: 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant=variant,
            )
        )

    def test_hold_registry_loads_pending_and_disputed_burgundy_states(self) -> None:
        by_id = {hold.id: hold for hold in self.claims.holds}
        self.assertIn(
            "sitehold:fr:marsannay:pc-2026-red-white-pending-homologation",
            by_id,
        )
        self.assertIn(
            "sitehold:fr:marsannay:le-clos-white-pending-homologation",
            by_id,
        )
        self.assertIn("sitehold:fr:monthelie:les-crays-disputed", by_id)

        for hold in by_id.values():
            if hold.id.startswith("sitehold:fr:marsannay:"):
                self.assertIn("inao_marsannay_pc_cnaov_2026_06", hold.source_ids)
                self.assertIn("legifrance_marsannay_2026_vci_list", hold.source_ids)

    def test_marsannay_red_and_white_pending_site_is_explicitly_held(self) -> None:
        red = self.marsannay_origin("Les Longeroies", "red standard", "Pinot Noir")
        white = self.marsannay_origin("Les Longeroies", "white standard", "Chardonnay")

        for origin in (red, white):
            self.assertFalse(origin.site_claim_eligible)
            self.assertEqual(origin.site_claim_status, "site_claim_pending_homologation")
            self.assertEqual(
                origin.site_claim_rule_id,
                "sitehold:fr:marsannay:pc-2026-red-white-pending-homologation",
            )
            self.assertTrue(
                any(item.startswith("site_claim_hold:") for item in origin.site_claim_evidence)
            )

    def test_marsannay_le_clos_preserves_white_only_pending_scope(self) -> None:
        white = self.marsannay_origin("Le Clos", "white standard", "Chardonnay")
        red = self.marsannay_origin("Le Clos", "red standard", "Pinot Noir")

        self.assertFalse(white.site_claim_eligible)
        self.assertEqual(white.site_claim_status, "site_claim_pending_homologation")
        self.assertEqual(
            white.site_claim_rule_id,
            "sitehold:fr:marsannay:le-clos-white-pending-homologation",
        )

        self.assertFalse(red.site_claim_eligible)
        self.assertEqual(red.site_claim_status, "site_claim_rule_unverified")
        self.assertIsNone(red.site_claim_rule_id)

    def test_marsannay_rose_is_not_misclassified_as_pending_premier_cru(self) -> None:
        rose = self.marsannay_origin("Les Longeroies", "rose standard", "Pinot Noir")
        self.assertFalse(rose.site_claim_eligible)
        self.assertEqual(rose.site_claim_status, "site_claim_rule_unverified")
        self.assertIsNone(rose.site_claim_rule_id)

    def test_no_marsannay_premier_cru_legal_spec_is_promoted(self) -> None:
        registry = LegalSpecRegistry()
        for variant in ("red premier cru", "white premier cru", "premier cru"):
            self.assertIsNone(
                registry.resolve(
                    country="France",
                    appellation="Marsannay",
                    variant=variant,
                )
            )

    def test_monthelie_les_crays_is_not_in_current_canonical_pc_sites(self) -> None:
        monthelie_names = {
            site.name
            for site in self.catalog.named_sites
            if site.parent == "Monthélie"
            and site.site_type == "climat"
            and site.classification == "Premier Cru"
        }
        self.assertEqual(len(monthelie_names), 15)
        self.assertNotIn("Les Crays", monthelie_names)

        hold = next(
            hold
            for hold in self.claims.holds
            if hold.id == "sitehold:fr:monthelie:les-crays-disputed"
        )
        self.assertEqual(hold.status, "site_claim_disputed_legal_name")
        self.assertEqual(hold.physical_site_names, ("Les Crays",))


class BurgundyExactClaimNameRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.factory = WineOriginFactory()
        cls.preuses = next(
            site
            for site in cls.factory.catalog.named_sites
            if site.parent == "Chablis grand cru"
            and site.site_type == "climat"
            and site.name == "Preuses"
        )

    def request(self, claimed_site_name: str | None):
        return self.factory.create(
            OriginRequest(
                country="France",
                region="Chablis",
                appellation="Chablis grand cru",
                grapes={"Chardonnay": 100},
                vintage_year=2024,
                label_scope="regulated_gi",
                site_id=self.preuses.id,
                claimed_site_name=claimed_site_name,
                wine_variant="grand cru",
            )
        )

    def test_preuses_is_exact_legal_suffix_but_les_preuses_is_not(self) -> None:
        exact = self.request("Preuses")
        alias = self.request("Les Preuses")

        self.assertTrue(exact.site_claim_eligible)
        self.assertEqual(exact.site_claim_name, "Preuses")
        self.assertFalse(alias.site_claim_eligible)
        self.assertEqual(alias.site_claim_status, "site_claim_rule_conditions_not_met")
        self.assertEqual(alias.site_claim_name, "Les Preuses")

    def test_corton_charlemagne_has_no_loaded_component_climat_suffixes(self) -> None:
        component_sites = [
            site
            for site in self.factory.catalog.named_sites
            if site.parent == "Corton-Charlemagne"
            and site.site_type == "climat"
        ]
        self.assertFalse(component_sites)


if __name__ == "__main__":
    unittest.main()
