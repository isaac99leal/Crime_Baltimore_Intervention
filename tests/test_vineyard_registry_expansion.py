from __future__ import annotations

import unittest

from sommelier_v2.knowledge.catalog import normalize_name
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog


class VineyardRegistryExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = WorldWineKnowledgeCatalog()

    def test_registry_more_than_doubles_named_site_foundation(self) -> None:
        stats = self.catalog.stats()
        self.assertGreaterEqual(stats["named_sites"], 2100)
        # Burgundy + Alsace alone contribute 949. Jurisdiction syncs may add more.
        self.assertGreaterEqual(stats["named_sites_2026_expansion"], 949)
        self.assertGreaterEqual(stats["named_site_sources"], 30)
        self.assertGreaterEqual(stats["named_site_bulk_sources_discovered"], 4)

    def test_bivb_sites_are_parent_and_type_scoped(self) -> None:
        rows = self.catalog.sites(
            country="France",
            region="Bourgogne",
            parent="Gevrey-Chambertin",
            site_type="climat",
        )
        names = {normalize_name(row.name) for row in rows}
        self.assertIn(normalize_name("Clos Saint-Jacques"), names)
        self.assertIn(normalize_name("Les Cazetiers"), names)
        clos = next(row for row in rows if normalize_name(row.name) == normalize_name("Clos Saint-Jacques"))
        self.assertEqual(clos.classification, "Premier Cru")
        self.assertEqual(clos.legal_status, "official_appellation_climat")
        self.assertIn("bivb_gevrey", clos.source_ids)

    def test_same_spelling_can_be_climat_and_lieu_dit(self) -> None:
        rows = self.catalog.sites(
            country="France",
            region="Bourgogne",
            parent="Chassagne-Montrachet",
        )
        matches = [row for row in rows if normalize_name(row.name) == normalize_name("Les Chaumes")]
        self.assertEqual({row.site_type for row in matches}, {"climat", "lieu_dit"})
        self.assertEqual(len({row.id for row in matches}), 2)

    def test_alsace_51_grand_cru_names_are_materialized(self) -> None:
        rows = self.catalog.sites(
            country="France",
            region="Alsace",
            parent="Alsace Grand Cru",
            site_type="grand_cru_lieu_dit",
        )
        self.assertEqual(len(rows), 51)
        names = {normalize_name(row.name) for row in rows}
        self.assertIn(normalize_name("Rangen"), names)
        self.assertIn(normalize_name("Kaefferkopf"), names)
        self.assertIn(normalize_name("Zotzenberg"), names)

    def test_expansion_does_not_fabricate_physical_or_legal_detail(self) -> None:
        rows = self.catalog.sites(
            country="France",
            region="Bourgogne",
            parent="Vosne-Romanée",
            site_type="climat",
        )
        cros = next(row for row in rows if normalize_name(row.name) == normalize_name("Cros Parantoux"))
        self.assertIsNone(cros.owner)
        self.assertIsNone(cros.area_ha)
        self.assertIsNone(cros.latitude)
        self.assertIsNone(cros.longitude)
        self.assertIsNone(cros.elevation_min_m)
        self.assertIsNone(cros.elevation_max_m)
        self.assertIsNone(cros.slope_min_pct)
        self.assertIsNone(cros.slope_max_pct)
        self.assertEqual(cros.soil_terms, ())
        self.assertEqual(cros.permitted_grapes, ())
        self.assertEqual(cros.ownership_history, ())

    def test_every_materialized_site_source_resolves(self) -> None:
        known = set(self.catalog.named_site_sources)
        self.assertTrue(known)
        for site in self.catalog.named_sites:
            self.assertTrue(set(site.source_ids).issubset(known), site.id)

    def test_unmaterialized_bulk_targets_remain_explicit(self) -> None:
        bulk = self.catalog.named_site_bulk_sources
        self.assertIn("bourgogne_maps_bulk", bulk)
        self.assertIn("rlp_weinbergsrolle", bulk)
        self.assertIn("noe_rieden_open_data", bulk)
        self.assertIn("vienna_rieden", bulk)
        self.assertEqual(bulk["bourgogne_maps_bulk"].get("ingest_status"), "discovered_not_materialized")
        self.assertEqual(bulk["vienna_rieden"].get("ingest_status"), "discovered_not_materialized")


if __name__ == "__main__":
    unittest.main()
