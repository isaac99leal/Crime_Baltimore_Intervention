from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog


class ChassagneMontrachetLieuDitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = WorldWineKnowledgeCatalog()
        cls.items = AuthoritativeCatalogGenerator(catalog=cls.knowledge).generate(
            as_of_year=2026,
            include_site_claims=True,
        )

    def test_current_bivb_inventory_adds_46_identity_only_lieux_dits(self):
        lieux_dits = [
            site for site in self.knowledge.named_sites
            if site.parent == "Chassagne-Montrachet"
            and site.site_type == "lieu_dit"
            and site.legal_status == "documented_named_site"
        ]
        self.assertEqual(len(lieux_dits), 46)
        names = {site.name for site in lieux_dits}
        self.assertIn("Blanchot Dessous", names)
        self.assertIn("Puits Merdreaux", names)
        self.assertIn("Voillenot Dessous", names)

    def test_ordinary_lieux_dits_do_not_leak_into_authoritative_site_claims(self):
        vineyards = {
            item.wine.vineyard
            for item in self.items
            if item.wine.appellation == "Chassagne-Montrachet"
            and item.wine.vineyard
        }
        for name in (
            "Blanchot Dessous",
            "Puits Merdreaux",
            "Les Mouchottes",
            "Voillenot Dessous",
        ):
            self.assertNotIn(name, vineyards)

    def test_same_name_climat_and_lieu_dit_remain_distinct_identities(self):
        chaumes = [
            site for site in self.knowledge.named_sites
            if site.parent == "Chassagne-Montrachet"
            and site.name == "Les Chaumes"
        ]
        self.assertEqual(len(chaumes), 2)
        self.assertEqual({site.site_type for site in chaumes}, {"climat", "lieu_dit"})
        self.assertEqual(len({site.id for site in chaumes}), 2)


if __name__ == "__main__":
    unittest.main()
