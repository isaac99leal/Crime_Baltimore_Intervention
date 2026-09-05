from __future__ import annotations

import unittest

from sommelier_v2.knowledge import (
    SimulationPriors,
    WineKnowledgeCatalog,
    load_legacy_vintage_knowledge,
    state_at_age,
)


class KnowledgeCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = WineKnowledgeCatalog()

    def test_legacy_catalog_is_preserved(self):
        stats = self.catalog.stats()
        self.assertEqual(stats["legacy_varietal_records"], 338)
        self.assertEqual(stats["legacy_geographic_nodes"], 1998)

    def test_official_designations_expand_grape_identity_catalog(self):
        stats = self.catalog.stats()
        self.assertEqual(stats["official_grape_designations_ingested"], 475)
        self.assertGreater(stats["merged_variety_identities"], stats["legacy_variety_identity_clusters"])

    def test_legal_gi_registry_is_explicit(self):
        stats = self.catalog.stats()
        self.assertEqual(stats["us_avas"], 280)
        self.assertEqual(stats["australian_gis"], 114)
        self.assertEqual(stats["new_zealand_wine_gis"], 19)
        self.assertEqual(stats["explicit_legal_gis"], 413)
        self.assertTrue(all(gi.legal_status == "established_or_registered" for gi in self.catalog.legal_gis))

    def test_aliases_resolve_to_same_identity(self):
        syrah = self.catalog.grape("Syrah")
        shiraz = self.catalog.grape("Shiraz")
        self.assertIsNotNone(syrah)
        self.assertIs(syrah, shiraz)


class KnowledgeProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.priors = SimulationPriors()

    def test_process_prior_counts(self):
        self.assertEqual(len(self.priors.aging_archetypes), 14)
        self.assertEqual(len(self.priors.fermentation_programs), 18)
        self.assertEqual(len(self.priors.elevage_programs), 12)

    def test_fermentation_prior_has_process_dimensions(self):
        program = self.priors.fermentation_programs["reductive_aromatic_white"]
        self.assertEqual(program.kinetics.vessel_material, "stainless steel")
        self.assertIsNotNone(program.kinetics.peak_temp_c.typical)
        self.assertIsNotNone(program.yeast.target_yan_mg_l.typical)
        self.assertFalse(program.malolactic.enabled)

    def test_aging_curve_is_continuous(self):
        archetype = self.priors.aging_archetypes["structured_tannic_red"]
        young = state_at_age(archetype, 1.0)
        mature = state_at_age(archetype, 12.0)
        older = state_at_age(archetype, 30.0)
        self.assertGreater(young.primary_fruit, mature.primary_fruit)
        self.assertGreater(mature.tertiary, young.tertiary)
        self.assertGreater(older.oxidation, mature.oxidation)
        self.assertGreater(older.sediment, young.sediment)

    def test_legacy_vintage_table_is_preserved_without_fabricated_weather(self):
        vintages = load_legacy_vintage_knowledge()
        self.assertEqual(len(vintages), 388)
        self.assertEqual(len({v.gi_id for v in vintages}), 25)
        self.assertEqual(min(v.year for v in vintages), 1982)
        self.assertEqual(max(v.year for v in vintages), 2023)
        self.assertTrue(all(v.overall_quality is not None for v in vintages))
        self.assertTrue(all(v.climate.rainfall_mm is None for v in vintages))


if __name__ == "__main__":
    unittest.main()
