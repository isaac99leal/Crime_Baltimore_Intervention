from __future__ import annotations

import unittest

from sommelier_v2.knowledge.site_research import SiteResearchError, SiteResearchRegistry


class SiteResearchRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = SiteResearchRegistry()

    def test_recovered_willamette_corpus_scale(self):
        stats = self.registry.stats()
        self.assertEqual(stats.site_count, 11)
        self.assertEqual(stats.referenced_source_count, 16)
        self.assertEqual(stats.exact_block_count, 57)
        self.assertGreaterEqual(stats.observation_count, 84)
        self.assertGreaterEqual(stats.quality_flag_count, 1)
        self.assertGreaterEqual(stats.ava_count, 4)

    def test_every_site_source_reference_resolves(self):
        for site in self.registry.sites:
            self.assertTrue(site.source_refs)
            for source_ref in site.source_refs:
                source = self.registry.source(source_ref)
                self.assertIsNotNone(source)
                assert source is not None
                self.assertTrue(source.url.startswith(("https://", "http://")))

    def test_producer_site_evidence_does_not_become_legal_authority(self):
        for claim in (
            "ava_legal_boundary",
            "protected_origin_legal_status",
            "legal_site_claim",
            "authorized_grape_legality",
            "universal_terroir_sensory_rule",
        ):
            with self.assertRaises(SiteResearchError):
                self.registry.assert_can_establish(claim)

        self.registry.assert_can_establish("block_composition_observation")
        self.registry.assert_can_establish("site_viticulture_observation")

    def test_knudsen_block_12_conflict_is_not_collapsed(self):
        history = self.registry.block_history("us-or-knudsen-vineyards", "12")
        self.assertEqual(len(history), 3)
        self.assertEqual({obs.clone for obs in history}, {"4407", "828"})
        self.assertEqual({obs.fields.get("plantedYear") for obs in history}, {2010, 2012})

        flags = self.registry.quality_flags("us-or-knudsen-vineyards")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].severity, "material")
        self.assertIn("clone", flags[0].field_set)
        self.assertIn("plantedYear", flags[0].field_set)

    def test_lingua_franca_block_three_keeps_source_context_material(self):
        history = self.registry.block_history("us-or-lingua-franca-estate", "3")
        self.assertEqual(len(history), 2)
        self.assertEqual({obs.clone for obs in history}, {"PN777 selected rows", "PN115 component"})

    def test_unresolved_iota_block_name_is_not_invented(self):
        blocks = self.registry.observations(
            "us-or-iota-pelos-sandberg-vineyard", kind="exact_block"
        )
        unresolved = [obs for obs in blocks if obs.block_id == "unnamed-southwest-2006"]
        self.assertEqual(len(unresolved), 1)
        context = str(unresolved[0].fields.get("evidenceContext", ""))
        self.assertIn("requires UI/source reconciliation", context)

    def test_exact_block_fields_survive_normalization(self):
        history = self.registry.block_history("us-or-open-claim-vineyard", "1")
        self.assertEqual(len(history), 1)
        block = history[0]
        self.assertEqual(block.variety, "Chardonnay")
        self.assertEqual(block.clone, "95")
        self.assertEqual(block.rootstock, "101-14")
        self.assertEqual(block.fields.get("rows"), 78)
        self.assertEqual(block.fields.get("acres"), 2.02)

    def test_site_and_observation_fields_are_immutable(self):
        site = self.registry.site("us-or-open-claim-vineyard")
        self.assertIsNotNone(site)
        assert site is not None
        with self.assertRaises(TypeError):
            site.site_fields["invented"] = "no"  # type: ignore[index]
        with self.assertRaises(TypeError):
            site.observations[0].fields["invented"] = "no"  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
