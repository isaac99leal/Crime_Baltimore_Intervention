from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.vineyard_ownership import VineyardOwnershipRegistry


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
    "Romanée-Conti": ("Domaine de la Romanée-Conti", 1.8140),
    "La Tâche": ("Domaine de la Romanée-Conti", 6.0620),
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

    def test_all_eight_physical_vineyard_identities_are_loaded_once(self):
        rows = self.grand_cru_sites()
        self.assertEqual(len(rows), 8)
        self.assertEqual({row.name for row in rows}, ALL_GRAND_CRUS)

    def test_historical_monopole_identities_remain_canonical(self):
        rows = {
            site.name: site
            for site in self.grand_cru_sites()
            if site.site_type == "monopole"
        }
        self.assertEqual(set(rows), set(MONOPOLES))
        self.assertTrue(all(row.legal_status == "appellation_monopole" for row in rows.values()))
        self.assertEqual(rows["Romanée-Conti"].owner, "Domaine de la Romanée-Conti")
        self.assertEqual(rows["La Tâche"].owner, "Domaine de la Romanée-Conti")

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
        self.assertGreater(len(self.catalog.named_sites), 1400)
        self.assertTrue(any(site.parent == "Barolo DOCG" for site in self.catalog.named_sites))
        self.assertTrue(any(site.parent == "Gevrey-Chambertin" for site in self.catalog.named_sites))


class VosneGrandCruOwnershipObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VineyardOwnershipRegistry()

    def test_current_owner_and_area_are_separate_from_site_identity(self):
        self.assertEqual(len(self.registry.observations), 4)
        for name, (owner, area_ha) in MONOPOLES.items():
            row = self.registry.latest_for_site(
                name, country="France", region="Bourgogne"
            )
            self.assertIsNotNone(row, name)
            self.assertEqual(row.owner, owner)
            self.assertAlmostEqual(row.area_ha or 0.0, area_ha, places=4)
            self.assertEqual(row.ownership_status, "monopole")
            self.assertEqual(row.effective_as_of, "2026-09-05")
            self.assertTrue(row.source_ids)

    def test_registry_is_ready_for_time_series_without_identity_mutation(self):
        row = self.registry.latest_for_site("La Romanée")
        self.assertIsNotNone(row)
        self.assertEqual(row.owner, "Domaine du Comte Liger-Belair")
        self.assertEqual(self.registry.stats()["vineyard_ownership_sites"], 4)


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


if __name__ == "__main__":
    unittest.main()
