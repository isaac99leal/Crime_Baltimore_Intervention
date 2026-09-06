from __future__ import annotations

import unittest

from sommelier_v2.knowledge.vineyard_registry import (
    RECORD_IDENTITY_EVIDENCE_CLASSES,
    WorldWineKnowledgeCatalog,
)
from sommelier_v2.knowledge.catalog import normalize_name
from sommelier_v2.knowledge.site_claims import SiteClaimRegistry


class WorldVineyardRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = WorldWineKnowledgeCatalog()

    def test_registry_is_materially_world_scale(self) -> None:
        stats = self.catalog.stats()
        self.assertGreaterEqual(stats["named_sites"], 6500)
        self.assertGreaterEqual(stats["named_sites_2026_expansion"], 5400)
        self.assertGreaterEqual(stats["named_site_sources"], 20)
        self.assertGreaterEqual(stats["named_site_countries"], 4)
        self.assertGreaterEqual(stats["named_sites_with_area"], 1300)

    def test_semantic_homonyms_require_source_defined_record_identity(self) -> None:
        groups: dict[tuple[str, str, str, str, str], list[object]] = {}
        for row in self.catalog.named_sites:
            key = (
                normalize_name(row.country),
                normalize_name(row.region),
                normalize_name(row.parent or ""),
                normalize_name(row.site_type),
                normalize_name(row.name),
            )
            groups.setdefault(key, []).append(row)

        homonyms = [rows for rows in groups.values() if len(rows) > 1]
        self.assertTrue(homonyms)
        for rows in homonyms:
            self.assertEqual(len(rows), len({row.id for row in rows}))
            for row in rows:
                evidence_classes = {
                    self.catalog.named_site_sources[source_id].evidence_class
                    for source_id in row.source_ids
                    if source_id in self.catalog.named_site_sources
                }
                self.assertTrue(
                    evidence_classes & RECORD_IDENTITY_EVIDENCE_CLASSES,
                    msg=f"semantic homonym lacks source-defined identity authority: {row.id}",
                )

    def test_fixin_exact_six_premier_cru_climats(self) -> None:
        rows = self.catalog.sites(country="France", region="Bourgogne", parent="Fixin", site_type="climat")
        names = {normalize_name(row.name) for row in rows if row.classification == "Premier Cru"}
        expected = {
            normalize_name(name)
            for name in (
                "Clos de la Perrière",
                "Clos Napoléon",
                "Clos du Chapitre",
                "Les Meix Bas",
                "Arvelets",
                "Hervelets",
            )
        }
        self.assertEqual(names, expected)
        for row in rows:
            if normalize_name(row.name) in expected:
                self.assertEqual(row.legal_status, "official_appellation_climat")
                self.assertIn("bivb_fixin", row.source_ids)

    def test_vougeot_exact_four_premier_cru_climats(self) -> None:
        rows = self.catalog.sites(country="France", region="Bourgogne", parent="Vougeot", site_type="climat")
        names = {normalize_name(row.name) for row in rows if row.classification == "Premier Cru"}
        expected = {
            normalize_name(name)
            for name in ("Les Crâs", "Le Clos Blanc", "Les Petits Vougeots", "Clos de la Perrière")
        }
        self.assertEqual(names, expected)
        for row in rows:
            if normalize_name(row.name) in expected:
                self.assertIn("inao_vougeot_current", row.source_ids)
                self.assertIn("inao_vougeot_cdc_2010", row.source_ids)

    def test_same_spelling_climat_and_lieu_dit_remain_distinct(self) -> None:
        rows = self.catalog.sites(country="France", region="Bourgogne", parent="Chassagne-Montrachet")
        matches = [row for row in rows if normalize_name(row.name) == normalize_name("Les Chaumes")]
        self.assertEqual({row.site_type for row in matches}, {"climat", "lieu_dit"})
        self.assertEqual(len(matches), 2)

    def test_alsace_51_grand_crus_materialized(self) -> None:
        rows = self.catalog.sites(country="France", region="Alsace", parent="Alsace Grand Cru", site_type="grand_cru_lieu_dit")
        sourced = [row for row in rows if "inao_alsace_grand_cru_2025" in row.source_ids]
        self.assertEqual(len(sourced), 51)
        names = {normalize_name(row.name) for row in sourced}
        self.assertIn(normalize_name("Rangen"), names)
        self.assertIn(normalize_name("Kaefferkopf"), names)
        self.assertIn(normalize_name("Zotzenberg"), names)

    def test_lower_austria_current_wfs_snapshot(self) -> None:
        rows = [row for row in self.catalog.named_sites if "noe_rieden_wfs_2026" in row.source_ids]
        self.assertEqual(len(rows), 3386)
        self.assertEqual(sum(row.site_type == "ried" for row in rows), 2878)
        self.assertEqual(sum(row.site_type == "subried" for row in rows), 508)
        for row in rows:
            self.assertEqual(row.geometry_source_id, "noe_rieden_wfs_2026")

    def test_vienna_140_official_rieden_materialized(self) -> None:
        rows = [row for row in self.catalog.named_sites if "wien_rieden_regulation_2016" in row.source_ids]
        self.assertEqual(len(rows), 140)
        self.assertTrue(all(row.site_type == "ried" for row in rows))

    def test_rheinland_pfalz_2024_snapshot(self) -> None:
        rows = [row for row in self.catalog.named_sites if "rlp_weinlagen_register_2024" in row.source_ids]
        self.assertEqual(len(rows), 1533)
        self.assertGreaterEqual(sum(row.area_ha is not None for row in rows), 1300)
        garkammer = next(row for row in rows if row.id == "site:germany:rlp:einzellage:110140")
        self.assertIsNone(garkammer.area_ha)
        self.assertIn("k.A.", garkammer.notes)

    def test_unsourced_physical_detail_is_not_fabricated(self) -> None:
        rows = self.catalog.sites(country="France", region="Bourgogne", parent="Vosne-Romanée", site_type="climat")
        cros = next(row for row in rows if normalize_name(row.name) == normalize_name("Cros Parantoux"))
        self.assertIsNone(cros.latitude)
        self.assertIsNone(cros.longitude)
        self.assertIsNone(cros.elevation_min_m)
        self.assertIsNone(cros.elevation_max_m)
        self.assertIsNone(cros.slope_min_pct)
        self.assertIsNone(cros.slope_max_pct)
        self.assertEqual(cros.soil_terms, ())
        self.assertEqual(cros.permitted_grapes, ())

    def test_expansion_source_ids_resolve(self) -> None:
        known = set(self.catalog.named_site_sources)
        expansion_sources = self.catalog._named_site_expansion_source_ids
        self.assertTrue(expansion_sources)
        self.assertTrue(expansion_sources.issubset(known))
        for row in self.catalog.named_sites:
            used = set(row.source_ids) & expansion_sources
            self.assertTrue(used.issubset(known))

    def test_bulk_source_statuses_match_materialization(self) -> None:
        bulk = self.catalog.named_site_bulk_sources
        self.assertEqual(bulk["rlp_weinbergsrolle"]["materialized_records"], 1533)
        self.assertEqual(bulk["noe_rieden_open_data"]["materialized_records"], 3386)
        self.assertEqual(bulk["vienna_rieden"]["materialized_records"], 140)
        self.assertEqual(bulk["vienna_rieden"]["ingest_status"], "materialized_official_2016_regulation")
        self.assertEqual(bulk["bourgogne_maps_bulk"]["ingest_status"], "reviewed_subset_materialized")

    def test_fixin_and_vougeot_claim_rules_are_explicit(self) -> None:
        registry = SiteClaimRegistry()
        by_id = {rule.id: rule for rule in registry.rules}
        fixin = by_id["siteclaim:fr:fixin:premier-cru-climat"]
        vougeot = by_id["siteclaim:fr:vougeot:premier-cru-climat"]
        self.assertEqual(len(fixin.allowed_site_names), 6)
        self.assertEqual(len(vougeot.allowed_site_names), 4)
        self.assertIn("fixin_masa_2024_current", fixin.source_ids)
        self.assertIn("vougeot_inao_cdc", vougeot.source_ids)


if __name__ == "__main__":
    unittest.main()
