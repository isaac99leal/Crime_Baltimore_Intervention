from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog, VarietyAreaObservation
from sommelier_v2.knowledge.schema import GrapeKnowledge
from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


class ObservationIdentityTests(unittest.TestCase):
    def catalog(self, names, base=()):
        c = WorldWineKnowledgeCatalog.__new__(WorldWineKnowledgeCatalog)
        c.base = SimpleNamespace(grapes=list(base))
        c.world_area = [VarietyAreaObservation(n, area_2023_ha=i + 0.01, source_row=i + 2)
                        for i, n in enumerate(names)]
        c.country_area = []
        c.piwi_records = []
        c.commercial_observations = []
        c._merge_grape_universe()
        return c

    def test_accents_do_not_merge_or_pool_areas(self):
        c = self.catalog(["Antao Vaz", "Antão Vaz"])
        self.assertEqual(len(c.grapes), 2)
        self.assertNotEqual(c.grape("Antao Vaz").id, c.grape("Antão Vaz").id)
        self.assertEqual([r.prime_name for r in c.area_for("Antao Vaz")], ["Antao Vaz"])
        self.assertIsNone(c.grape("Antao-Vaz"))

    def test_existing_profile_is_not_enriched_by_folded_census_name(self):
        base = GrapeKnowledge("grape:existing", "Sémillon")
        c = self.catalog(["Semillon"], [base])
        self.assertNotIn("census_prime_name", base.tags)
        self.assertEqual(c.area_for("Sémillon"), [])
        self.assertEqual(len(c.area_for("Semillon")), 1)

    def test_duplicate_source_rows_remain_observations_not_new_botanical_species(self):
        c = self.catalog(["Bordô", "Bordô"])
        self.assertEqual(len(c.grapes), 1)
        self.assertEqual(len(c.area_for("Bordô")), 2)
        self.assertEqual([r.source_row for r in c.world_area], [2, 3])

    def test_colliding_existing_alias_is_unknown_not_last_writer(self):
        c = self.catalog([], [GrapeKnowledge("g:1", "First", aliases=["Shared"]),
                              GrapeKnowledge("g:2", "Second", aliases=["Shared"])])
        self.assertIsNone(c.grape("Shared"))
        self.assertEqual(len(c.grape_name_candidates["shared"]), 2)

    def test_repeated_ambiguous_source_name_has_one_unresolved_candidate(self):
        c = self.catalog(["Shared", "Shared"], [GrapeKnowledge("g:1", "First", aliases=["Shared"]),
                                               GrapeKnowledge("g:2", "Second", aliases=["Shared"])])
        self.assertEqual(len(c.grapes), 3)
        self.assertIsNone(c.grape("Shared"))
        self.assertEqual(len(c.area_for("Shared")), 2)

    def test_documented_existing_alias_still_resolves(self):
        c = self.catalog([], [GrapeKnowledge("g:1", "Syrah", aliases=["Shiraz"])])
        self.assertIs(c.grape("Syrah"), c.grape("Shiraz"))

    def test_collision_ids_do_not_depend_on_source_row_order(self):
        names = ["Antao Vaz", "Antão Vaz"]
        first = self.catalog(names)
        second = self.catalog(list(reversed(names)))
        self.assertEqual({g.name: g.id for g in first.grapes}, {g.name: g.id for g in second.grapes})

    def test_catalog_exposes_evidence_resolution_separately_from_name_lookup(self):
        c = self.catalog(["Cabernet Sauvignon"])
        self.assertIsNotNone(c.grape("Cabernet Sauvignon"))
        decision = c.resolve_variety_identity("Cabernet Sauvignon")
        self.assertTrue(decision.identity_confirmed)
        self.assertEqual(decision.canonical_id, "vivc:1929")

    def test_all_country_rows_survive_without_fake_country(self):
        c = WorldWineKnowledgeCatalog.__new__(WorldWineKnowledgeCatalog)
        c.world_area, c.country_area, c.unresolved_country_area = [], [], []
        c._load_area()
        self.assertEqual(len(c.country_area), 4705)
        self.assertEqual(len(c.unresolved_country_area), 102)
        self.assertTrue(all(r.country is None and r.country_as_reported is not None
                            for r in c.unresolved_country_area))
        self.assertEqual(len({r.source_row for r in c.country_area + c.unresolved_country_area}), 4807)


class EvidenceResolverTests(unittest.TestCase):
    def document(self):
        return {
            "snapshot_version": "test", "identities": [{"id": "vivc:1", "vivc_id": 1}],
            "evidence": {"e:1": {"authority_type": "botanical_registry", "review_status": "reviewed",
                "canonical_id": "vivc:1", "source_id": "test-census", "source_name": "Cépage",
                "relation": "exact_identity", "url": "https://example.test/record/1", "retrieved_on": "2026-09-07"}},
            "links": [{"source_id": "test-census", "source_name": "Cépage", "canonical_id": "vivc:1",
                       "level": "R5", "evidence_ids": ["e:1"]}],
        }

    def load(self, doc):
        with TemporaryDirectory() as directory:
            p = Path(directory) / "evidence.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            return VarietyIdentityRegistry(p)

    def test_reviewed_exact_link_and_unreviewed_folded_candidate(self):
        r = self.load(self.document())
        self.assertTrue(r.resolve("Cépage", source_id="test-census").identity_confirmed)
        folded = r.resolve("Cepage", source_id="test-census")
        self.assertEqual(folded.level, "R2")
        self.assertIsNone(folded.canonical_id)

    def test_review_cannot_be_borrowed_from_another_assertion(self):
        d = self.document()
        d["evidence"]["e:1"]["source_name"] = "Another name"
        with self.assertRaises(ValueError):
            self.load(d)

    def test_search_snippet_cannot_be_promoted(self):
        d = self.document()
        d["evidence"]["e:1"]["review_status"] = "candidate_only"
        with self.assertRaises(ValueError):
            self.load(d)

    def test_source_and_country_scope_are_required(self):
        d = self.document()
        d["links"][0]["country"] = d["evidence"]["e:1"]["country"] = "Testland"
        r = self.load(d)
        self.assertFalse(r.resolve("Cépage", source_id="test-census").identity_confirmed)
        self.assertFalse(r.resolve("Cépage", source_id="another-census", country="Testland").identity_confirmed)
        self.assertTrue(r.resolve("Cépage", source_id="test-census", country="Testland").identity_confirmed)

    def test_conflicting_identity_blocks_even_when_one_link_is_reviewed(self):
        d = self.document()
        d["identities"].append({"id": "vivc:2", "vivc_id": 2})
        d["links"].append(dict(d["links"][0], canonical_id="vivc:2", level="R2"))
        result = self.load(d).resolve("Cépage", source_id="test-census")
        self.assertEqual(result.status, "CONFLICT")
        self.assertIsNone(result.canonical_id)

    def test_first_reviewed_adelaide_links_resolve_exactly(self):
        r = VarietyIdentityRegistry()
        expected = {
            "Cabernet Sauvignon": "vivc:1929",
            "Syrah": "vivc:11748",
            "Rondo": "vivc:14308",
            "Moschofilero": "vivc:8068",
            "Merlot": "vivc:7657",
            "Chardonnay": "vivc:2455",
            "Tempranillo": "vivc:12350",
            "Airén": "vivc:157",
        }
        for source_name, canonical_id in expected.items():
            decision = r.resolve(source_name, source_id="adelaide_2025")
            self.assertTrue(decision.identity_confirmed, source_name)
            self.assertEqual(decision.status, "RESOLVED")
            self.assertEqual(decision.level, "R5")
            self.assertEqual(decision.canonical_id, canonical_id)

    def test_resolution_remains_source_scoped(self):
        r = VarietyIdentityRegistry()
        for source_name in (
            "Cabernet Sauvignon", "Syrah", "Rondo", "Moschofilero",
            "Merlot", "Chardonnay", "Tempranillo", "Airén",
        ):
            self.assertFalse(r.resolve(source_name, source_id="another-census").identity_confirmed)

    def test_accent_fold_is_not_promoted_without_exact_source_assertion(self):
        r = VarietyIdentityRegistry()
        exact = r.resolve("Airén", source_id="adelaide_2025")
        folded = r.resolve("Airen", source_id="adelaide_2025")
        self.assertTrue(exact.identity_confirmed)
        self.assertEqual(folded.status, "CANDIDATE")
        self.assertEqual(folded.level, "R2")
        self.assertIsNone(folded.canonical_id)

    def test_unseen_and_unreviewed_names_stay_unknown(self):
        r = VarietyIdentityRegistry()
        self.assertEqual(r.resolve("Unseen", source_id="adelaide_2025").status, "UNKNOWN")
        self.assertEqual(r.resolve("Pinot Noir", source_id="adelaide_2025").status, "UNKNOWN")
        self.assertEqual(r.resolve("Sauvignon Blanc", source_id="adelaide_2025").status, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
