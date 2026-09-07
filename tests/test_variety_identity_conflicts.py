from __future__ import annotations

import unittest

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry


class VarietyIdentityConflictQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_conflict_queue_is_source_backed_and_blocks_promotion(self):
        self.assertGreaterEqual(len(self.registry.conflicts), 2)
        for conflict in self.registry.conflicts:
            self.assertEqual(conflict.generator_policy, "block_identity_promotion")
            self.assertTrue(conflict.evidence_ids)
            self.assertTrue(
                all(evidence_id in self.registry.conflict_evidence for evidence_id in conflict.evidence_ids)
            )

    def test_petit_verdot_exposes_two_competing_vivc_candidates(self):
        decision = self.registry.resolve("Petit Verdot", source_id="adelaide_2025")
        self.assertEqual(decision.status, "CONFLICT")
        self.assertEqual(decision.level, "R0")
        self.assertEqual(decision.candidate_ids, ("vivc:12973", "vivc:12974"))
        self.assertFalse(decision.identity_confirmed)
        self.assertIsNone(decision.canonical_id)

    def test_catarratto_bianco_is_explicit_umbrella_conflict(self):
        decision = self.registry.resolve("Catarratto Bianco", source_id="adelaide_2025")
        self.assertEqual(decision.status, "CONFLICT")
        self.assertEqual(decision.level, "R0")
        self.assertEqual(decision.candidate_ids, ("vivc:2341",))
        self.assertIn("umbrella_name_requires_subtype_resolution", decision.reason)
        self.assertFalse(decision.identity_confirmed)

    def test_conflicts_remain_source_scoped(self):
        for source_name in ("Petit Verdot", "Catarratto Bianco"):
            self.assertEqual(
                self.registry.resolve(source_name, source_id="another-census").status,
                "UNKNOWN",
            )

    def test_explicit_evidence_document_does_not_import_default_conflicts(self):
        # Existing isolated-data-path tests depend on this invariant. The default
        # conflict queue must never leak into callers validating a separate source.
        from pathlib import Path
        from tempfile import TemporaryDirectory
        import json

        doc = {
            "snapshot_version": "isolated",
            "evidence": {
                "e:1": {
                    "authority_type": "botanical_registry",
                    "review_status": "reviewed",
                    "canonical_id": "vivc:1",
                    "source_id": "test-source",
                    "source_name": "Petit Verdot",
                    "country": None,
                    "relation": "exact_identity",
                    "url": "https://example.test/1",
                    "retrieved_on": "2026-09-07",
                }
            },
            "identities": [{"id": "vivc:1", "vivc_id": 1}],
            "links": [{
                "source_id": "test-source",
                "source_name": "Petit Verdot",
                "canonical_id": "vivc:1",
                "level": "R5",
                "evidence_ids": ["e:1"],
            }],
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            registry = VarietyIdentityRegistry(path)
            self.assertFalse(registry.conflicts)
            self.assertTrue(
                registry.resolve("Petit Verdot", source_id="test-source").identity_confirmed
            )


if __name__ == "__main__":
    unittest.main()
