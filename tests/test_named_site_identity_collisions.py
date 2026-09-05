from __future__ import annotations

import unittest

from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog


class NamedSiteIdentityCollisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = WorldWineKnowledgeCatalog()

    def test_same_name_climat_and_lieu_dit_are_distinct_records(self):
        cases = (
            ("Volnay", "La Gigotte"),
            ("Volnay", "Le Village"),
            ("Volnay", "Les Lurets"),
            ("Saint-Aubin", "Le Puits"),
            ("Saint-Aubin", "Les Castets"),
        )
        for parent, name in cases:
            rows = [
                site
                for site in self.catalog.named_sites
                if site.parent == parent and site.name == name
            ]
            self.assertEqual(
                {site.site_type for site in rows},
                {"climat", "lieu_dit"},
                (parent, name, rows),
            )
            self.assertEqual(len({site.id for site in rows}), 2, (parent, name, rows))

    def test_first_existing_id_remains_stable_for_legal_climat(self):
        site = next(
            site
            for site in self.catalog.named_sites
            if site.parent == "Volnay"
            and site.name == "Le Village"
            and site.site_type == "climat"
        )
        self.assertEqual(site.id, "site:france:bourgogne:volnay:le-village")

    def test_colliding_lieu_dit_gets_typed_suffix(self):
        site = next(
            site
            for site in self.catalog.named_sites
            if site.parent == "Volnay"
            and site.name == "Le Village"
            and site.site_type == "lieu_dit"
        )
        self.assertEqual(
            site.id,
            "site:france:bourgogne:volnay:le-village:lieu-dit",
        )


if __name__ == "__main__":
    unittest.main()
