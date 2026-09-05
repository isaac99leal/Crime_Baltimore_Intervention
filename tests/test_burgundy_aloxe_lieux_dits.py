from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog


class AloxeCortonLieuDitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = WorldWineKnowledgeCatalog()
        cls.items = AuthoritativeCatalogGenerator(catalog=cls.knowledge).generate(
            as_of_year=2026, include_site_claims=True
        )

    def test_current_inventory_adds_15_identity_only_lieux_dits(self):
        sites = [
            site for site in self.knowledge.named_sites
            if site.parent == "Aloxe-Corton"
            and site.site_type == "lieu_dit"
            and site.legal_status == "documented_named_site"
        ]
        self.assertEqual(len(sites), 15)
        names = {site.name for site in sites}
        self.assertIn("Boulmeau", names)
        self.assertIn("Les Petits Vercots", names)
        self.assertIn("Les Valozières", names)

    def test_ordinary_lieux_dits_do_not_become_premier_cru_claims(self):
        vineyards = {
            item.wine.vineyard
            for item in self.items
            if item.wine.appellation == "Aloxe-Corton" and item.wine.vineyard
        }
        for ordinary_name in ("Boulmeau", "Les Petits Vercots", "Les Morais"):
            self.assertNotIn(ordinary_name, vineyards)

    def test_les_valozieres_climat_and_lieu_dit_are_distinct_typed_identities(self):
        rows = [
            site for site in self.knowledge.named_sites
            if site.parent == "Aloxe-Corton" and site.name == "Les Valozières"
        ]
        self.assertEqual(len(rows), 2)
        self.assertEqual({site.site_type for site in rows}, {"climat", "lieu_dit"})
        self.assertEqual(len({site.id for site in rows}), 2)


if __name__ == "__main__":
    unittest.main()
