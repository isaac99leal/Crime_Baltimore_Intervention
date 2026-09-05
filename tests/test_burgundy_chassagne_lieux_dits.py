from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog


class ChassagneMontrachetLieuDitIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = WorldWineKnowledgeCatalog()
        cls.sites = [
            site
            for site in cls.catalog.named_sites
            if site.parent == "Chassagne-Montrachet"
        ]

    def test_current_inventory_retains_both_site_classes(self):
        climats = [site for site in self.sites if site.site_type == "climat"]
        lieux_dits = [site for site in self.sites if site.site_type == "lieu_dit"]
        self.assertEqual(len(climats), 55)
        self.assertEqual(len(lieux_dits), 46)
        self.assertEqual(len(self.sites), 101)
        self.assertEqual(
            {site.legal_status for site in climats},
            {"official_appellation_climat"},
        )
        self.assertEqual(
            {site.legal_status for site in lieux_dits},
            {"official_appellation_lieu_dit"},
        )

    def test_les_chaumes_climat_and_lieu_dit_do_not_collapse(self):
        rows = [site for site in self.sites if site.name == "Les Chaumes"]
        self.assertEqual(len(rows), 2)
        self.assertEqual({site.site_type for site in rows}, {"climat", "lieu_dit"})
        self.assertEqual(len({site.id for site in rows}), 2)

        climat = next(site for site in rows if site.site_type == "climat")
        lieu_dit = next(site for site in rows if site.site_type == "lieu_dit")
        self.assertEqual(climat.classification, "Premier Cru")
        self.assertEqual(climat.legal_status, "official_appellation_climat")
        self.assertIsNone(lieu_dit.classification)
        self.assertEqual(lieu_dit.legal_status, "official_appellation_lieu_dit")

    def test_representative_ordinary_lieux_dits_are_identity_only(self):
        by_name = {site.name: site for site in self.sites if site.site_type == "lieu_dit"}
        for name in ("Puits Merdreaux", "Les Houillères", "Blanchot Dessous"):
            self.assertIn(name, by_name)
            self.assertEqual(by_name[name].legal_status, "official_appellation_lieu_dit")
            self.assertNotEqual(by_name[name].classification, "Premier Cru")


class ChassagneMontrachetLieuDitMarketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [
            item
            for item in AuthoritativeCatalogGenerator().generate(
                as_of_year=2026,
                include_site_claims=True,
            )
            if item.wine.appellation == "Chassagne-Montrachet"
        ]

    def test_identity_expansion_does_not_change_strict_market_size(self):
        self.assertEqual(len(self.rows), 171)

    def test_ordinary_only_lieux_dits_remain_fail_closed_for_labels(self):
        vineyards = {item.wine.vineyard for item in self.rows if item.wine.vineyard}
        self.assertNotIn("Puits Merdreaux", vineyards)
        self.assertNotIn("Les Houillères", vineyards)
        self.assertNotIn("Blanchot Dessous", vineyards)

    def test_same_name_les_chaumes_can_enter_only_via_premier_cru_climat_identity(self):
        rows = [item for item in self.rows if item.wine.vineyard == "Les Chaumes"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            {item.legal_spec_id for item in rows},
            {
                "fr:chassagne-montrachet:white-premier-cru",
                "fr:chassagne-montrachet:red-premier-cru",
            },
        )
        self.assertTrue(all(item.generated.evidence.site_claim_eligible for item in rows))
        self.assertTrue(
            all(
                item.generated.evidence.site_claim_rule_id
                == "siteclaim:fr:chassagne-montrachet:premier-cru-climat"
                for item in rows
            )
        )


if __name__ == "__main__":
    unittest.main()
