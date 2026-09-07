from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_bulk import BulkVarietyRegistry


class BulkVarietyRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = BulkVarietyRegistry()
        cls.records = cls.registry.all_records()
        cls.by_name = {row.source_name: row for row in cls.records}

    def test_every_literal_adelaide_name_has_operational_record(self):
        source_names = {row.prime_name.casefold() for row in self.registry.catalog.world_area}
        operational = {row.source_name.casefold() for row in self.records}
        self.assertEqual(operational, source_names)
        self.assertTrue(all(row.simulation_enabled for row in self.records))

    def test_bulk_layer_never_infers_gi_entitlement(self):
        self.assertTrue(all(not row.legal_gi_entitlement_inferred for row in self.records))
        self.assertTrue(
            all(not row.legal_gi_entitlement_inferred for row in self.registry.all_global_records())
        )

    def test_vivc_only_canonical_identities_are_operational(self):
        vivc_only = self.registry.vivc_only_records()
        self.assertTrue(vivc_only)
        self.assertTrue(all(row.source_id == "vivc_registry" for row in vivc_only))
        self.assertTrue(all(row.identity_confirmed for row in vivc_only))
        self.assertTrue(all(row.simulation_enabled for row in vivc_only))
        self.assertTrue(all(row.world_area_2023_ha == 0.0 for row in vivc_only))

    def test_uncertain_identity_does_not_block_simulation(self):
        for name in ("Petit Verdot", "Catarratto Bianco", "Beba", "Pamid"):
            row = self.by_name[name]
            self.assertEqual(row.identity_level, "R0")
            self.assertFalse(row.identity_confirmed)
            self.assertTrue(row.simulation_enabled)

    def test_r3_candidates_are_operational_without_false_confirmation(self):
        for name in ("Cereza", "Criolla Grande", "Torrontés Riojano", "Pedro Giménez"):
            row = self.by_name[name]
            self.assertEqual(row.identity_level, "R3")
            self.assertFalse(row.identity_confirmed)
            self.assertTrue(row.candidate_ids)
            self.assertTrue(row.simulation_enabled)

    def test_ttb_data_marks_obscure_us_commercial_plausibility(self):
        for name in ("Assyrtiko", "Baga", "Caladoc", "Loureiro", "Marselan", "Vranac", "Verdejo"):
            row = self.by_name[name]
            self.assertIsNotNone(row.ttb_status, name)
            self.assertEqual(row.spatial_state_us, "COMMERCIALLY_PLAUSIBLE")

    def test_growth_plausibility_distinguishes_observed_ttb_and_analogue(self):
        observed = self.registry.assess_country_plausibility("Côt", "Argentina")
        self.assertEqual(observed.state, "OBSERVED")
        self.assertFalse(observed.legal_entitlement_inferred)

        us = self.registry.assess_country_plausibility("Assyrtiko", "United States")
        self.assertEqual(us.state, "COMMERCIALLY_PLAUSIBLE")
        self.assertFalse(us.legal_entitlement_inferred)

        analogue = self.registry.assess_country_plausibility("Shesh i Zi", "New Zealand")
        self.assertIn(
            analogue.state,
            {"AGRONOMICALLY_PLAUSIBLE", "EXPERIMENTALLY_PLAUSIBLE"},
        )
        self.assertFalse(analogue.legal_entitlement_inferred)

    def test_observed_country_geography_is_preserved(self):
        malbec = self.by_name["Côt"]
        self.assertIn("Argentina", malbec.observed_countries)
        self.assertIn("Argentina", malbec.new_world_observed_countries)

        shiraz = self.by_name["Syrah"]
        self.assertIn("Australia", shiraz.new_world_observed_countries)

    def test_trait_priors_exist_for_sparse_and_deep_records(self):
        for name in ("Cabernet Sauvignon", "Cereza", "Beba", "Shesh i Zi"):
            row = self.by_name[name]
            self.assertTrue(row.style_family)
            self.assertTrue(row.fermentation_archetype)
            self.assertIsNotNone(row.traits.acidity.typical)
            self.assertIsNotNone(row.traits.tannin.typical)
            self.assertIsNotNone(row.traits.body.typical)
            self.assertIsNotNone(row.traits.alcohol_pct.typical)
            self.assertIsNotNone(row.traits.fermentation_temp_c.typical)
            self.assertGreaterEqual(row.traits.malolactic_probability, 0.0)
            self.assertLessEqual(row.traits.malolactic_probability, 1.0)

    def test_unknown_color_gets_broad_prior_not_fake_specificity(self):
        row = self.by_name["Shesh i Zi"]
        self.assertIn(row.traits.confidence, {"low", "medium"})
        self.assertEqual(row.traits.source, "generic_commercial_simulation_prior")

    def test_world_catalog_exposes_operational_layer_directly(self):
        world = self.registry.catalog
        record = world.operational_variety("Assyrtiko")
        self.assertTrue(record.simulation_enabled)
        self.assertEqual(record.source_name, "Assyrtiko")
        decision = world.assess_variety_country_plausibility("Assyrtiko", "United States")
        self.assertEqual(decision.state, "COMMERCIALLY_PLAUSIBLE")
        self.assertFalse(decision.legal_entitlement_inferred)

    def test_stats_report_full_operational_coverage(self):
        stats = self.registry.stats()
        self.assertEqual(stats["operational_adelaide_names"], len(self.records))
        self.assertGreaterEqual(stats["vivc_identity_records_loaded"], 100)
        self.assertGreater(stats["global_operational_records"], len(self.records))
        self.assertEqual(stats["simulation_enabled"], stats["global_operational_records"])
        self.assertGreater(stats["ttb_supported_names"], 100)
        self.assertGreater(stats["new_world_observed_names"], 100)
        self.assertGreater(stats["world_area_2023_ha"], 4_000_000)
        self.assertGreater(stats["strong_identity_area_2023_pct"], 70.0)
        self.assertGreater(stats["legacy_specific_trait_profiles"], 100)
        self.assertGreater(stats["specific_style_families"], 100)


if __name__ == "__main__":
    unittest.main()
