from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog


ALL_GRAND_CRUS = {
    "Echezeaux",
    "Grands-Echezeaux",
    "Romanée-Saint-Vivant",
    "Romanée-Conti",
    "La Romanée",
    "La Tâche",
    "Richebourg",
    "La Grande Rue",
}

MONOPOLES = {
    "Romanée-Conti": ("Société Civile du Domaine de la Romanée-Conti", 1.8140),
    "La Tâche": ("Société Civile du Domaine de la Romanée-Conti", 6.0620),
    "La Romanée": ("Domaine du Comte Liger-Belair", 0.8452),
    "La Grande Rue": ("Domaine Nicole Lamarche", 1.65),
}


class VosneGrandCruIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = WorldWineKnowledgeCatalog()

    def grand_cru_sites(self):
        return [
            site
            for site in self.catalog.named_sites
            if site.classification == "Grand Cru"
            and site.name in ALL_GRAND_CRUS
            and site.site_type in {"grand_cru_vineyard", "monopole"}
        ]

    def test_all_eight_physical_vineyard_identities_are_loaded(self):
        rows = self.grand_cru_sites()
        self.assertEqual(len(rows), 8)
        self.assertEqual({row.name for row in rows}, ALL_GRAND_CRUS)

    def test_four_vosne_monopoles_are_explicit(self):
        rows = {
            site.name: site
            for site in self.grand_cru_sites()
            if site.site_type == "monopole"
        }
        self.assertEqual(set(rows), set(MONOPOLES))
        for name, (owner, area_ha) in MONOPOLES.items():
            self.assertEqual(rows[name].owner, owner)
            self.assertAlmostEqual(rows[name].area_ha or 0.0, area_ha, places=4)
            self.assertEqual(rows[name].legal_status, "official_grand_cru_monopole")

    def test_multi_owner_grand_crus_are_not_misclassified_as_monopoles(self):
        rows = {site.name: site for site in self.grand_cru_sites()}
        for name in {
            "Echezeaux",
            "Grands-Echezeaux",
            "Romanée-Saint-Vivant",
            "Richebourg",
        }:
            self.assertEqual(rows[name].site_type, "grand_cru_vineyard")
            self.assertIsNone(rows[name].owner)

    def test_named_site_file_discovery_preserves_existing_registry(self):
        # The newly discovered tranche must extend the existing registry rather
        # than replacing the legacy seed/supplement files.
        self.assertGreater(len(self.catalog.named_sites), 1400)
        self.assertTrue(any(site.parent == "Barolo DOCG" for site in self.catalog.named_sites))
        self.assertTrue(any(site.parent == "Gevrey-Chambertin" for site in self.catalog.named_sites))


class GrandCruIdentityDoesNotDuplicateLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = AuthoritativeCatalogGenerator().generate(
            as_of_year=2026, include_site_claims=True
        )

    def test_physical_identity_is_not_emitted_as_second_site_claim(self):
        rows = [
            item
            for item in self.items
            if item.wine.appellation in ALL_GRAND_CRUS
            and item.wine.classification == "grand cru"
        ]
        self.assertEqual({item.wine.appellation for item in rows}, ALL_GRAND_CRUS)
        self.assertTrue(all(not item.wine.vineyard for item in rows))
        self.assertTrue(all(item.site_claim_rule_id is None for item in rows))


if __name__ == "__main__":
    unittest.main()
