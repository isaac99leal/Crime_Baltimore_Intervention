from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


class LegalSpecAmendmentSafetyTests(unittest.TestCase):
    def registry_from(self, document: dict) -> LegalSpecRegistry:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "legal_gi_specs_test.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            return LegalSpecRegistry(data_path=path)

    @staticmethod
    def base_document() -> dict:
        return {
            "sources": {
                "source:base": {"authority": "Base authority"},
                "source:new": {"authority": "New authority"},
            },
            "specs": [
                {
                    "id": "test:origin:standard",
                    "country": "Testland",
                    "appellation": "Test Origin",
                    "variant": "standard",
                    "allowed_grapes": ["Test Grape"],
                    "min_potential_alcohol_pct": 10.5,
                    "release_year_offset": 1,
                    "source_ids": ["source:base"],
                    "notes": "Base note.",
                }
            ],
            "amendments": [],
        }

    def test_missing_field_can_be_filled_and_evidence_appended(self):
        doc = self.base_document()
        doc["amendments"] = [
            {
                "id": "amend:test:1",
                "target_id": "test:origin:standard",
                "set": {"min_must_sugar_g_l": 180, "earliest_release_month": 6, "earliest_release_day": 30},
                "add_source_ids": ["source:new"],
                "append_notes": "Exact maturity and release evidence.",
            }
        ]
        registry = self.registry_from(doc)
        spec = registry.resolve(country="Testland", appellation="Test Origin")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.min_must_sugar_g_l, 180.0)
        self.assertEqual((spec.earliest_release_month, spec.earliest_release_day), (6, 30))
        self.assertEqual(spec.source_ids, ("source:base", "source:new"))
        self.assertIn("Exact maturity and release evidence.", spec.notes)
        self.assertEqual(registry.applied_amendment_ids, ("amend:test:1",))
        self.assertEqual(registry.stats()["legal_spec_amendments_applied"], 1)

    def test_identical_restatement_is_allowed_including_numeric_equivalence(self):
        doc = self.base_document()
        doc["amendments"] = [
            {
                "id": "amend:test:identical",
                "target_id": "test:origin:standard",
                "set": {"min_potential_alcohol_pct": 10.5, "release_year_offset": 1.0},
            }
        ]
        registry = self.registry_from(doc)
        spec = registry.resolve(country="Testland", appellation="Test Origin")
        self.assertEqual(spec.min_potential_alcohol_pct, 10.5)
        self.assertEqual(spec.release_year_offset, 1)

    def test_conflicting_known_value_fails_closed(self):
        doc = self.base_document()
        doc["amendments"] = [
            {
                "id": "amend:test:conflict",
                "target_id": "test:origin:standard",
                "set": {"min_potential_alcohol_pct": 11.0},
            }
        ]
        with self.assertRaisesRegex(ValueError, "conflicts with test:origin:standard.min_potential_alcohol_pct"):
            self.registry_from(doc)

    def test_identity_fields_are_never_amendable(self):
        doc = self.base_document()
        doc["amendments"] = [
            {
                "id": "amend:test:identity",
                "target_id": "test:origin:standard",
                "set": {"appellation": "Other Origin"},
            }
        ]
        with self.assertRaisesRegex(ValueError, "field is not amendable: appellation"):
            self.registry_from(doc)

    def test_unknown_target_and_unknown_source_fail_closed(self):
        unknown_target = self.base_document()
        unknown_target["amendments"] = [
            {"id": "amend:test:unknown-target", "target_id": "missing:spec", "set": {"min_must_sugar_g_l": 180}}
        ]
        with self.assertRaisesRegex(ValueError, "targets unknown legal specification"):
            self.registry_from(unknown_target)

        unknown_source = self.base_document()
        unknown_source["amendments"] = [
            {
                "id": "amend:test:unknown-source",
                "target_id": "test:origin:standard",
                "add_source_ids": ["source:missing"],
            }
        ]
        with self.assertRaisesRegex(ValueError, "references unknown legal sources"):
            self.registry_from(unknown_source)

    def test_duplicate_amendment_ids_fail_closed(self):
        doc = self.base_document()
        doc["amendments"] = [
            {"id": "amend:test:duplicate", "target_id": "test:origin:standard", "set": {"min_must_sugar_g_l": 180}},
            {"id": "amend:test:duplicate", "target_id": "test:origin:standard", "set": {"max_total_alcohol_pct": 13.5}},
        ]
        with self.assertRaisesRegex(ValueError, "Duplicate legal specification amendment id"):
            self.registry_from(doc)

    def test_boolean_is_not_treated_as_numeric_one(self):
        doc = self.base_document()
        doc["specs"][0]["manual_harvest_required"] = True
        doc["amendments"] = [
            {
                "id": "amend:test:bool-numeric",
                "target_id": "test:origin:standard",
                "set": {"manual_harvest_required": 1},
            }
        ]
        with self.assertRaisesRegex(ValueError, "conflicts with test:origin:standard.manual_harvest_required"):
            self.registry_from(doc)


class ChambolleAmendmentIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()
        cls.standard = cls.registry.resolve(
            country="France", appellation="Chambolle-Musigny", variant="standard"
        )
        cls.premier = cls.registry.resolve(
            country="France", appellation="Chambolle-Musigny", variant="premier cru"
        )

    def test_two_chambolle_amendments_are_applied(self):
        self.assertIn(
            "fr:chambolle-musigny:standard:masa-2011-enrichment",
            self.registry.applied_amendment_ids,
        )
        self.assertIn(
            "fr:chambolle-musigny:premier-cru:masa-2011-enrichment",
            self.registry.applied_amendment_ids,
        )
        self.assertIsNotNone(self.standard)
        self.assertIsNotNone(self.premier)
        self.assertIn("chambolle_masa_2011_cdc", self.standard.source_ids)
        self.assertIn("chambolle_masa_2011_cdc", self.premier.source_ids)

    def test_exact_maturity_and_total_alcohol_fields_are_enriched(self):
        self.assertEqual(self.standard.min_must_sugar_g_l, 180.0)
        self.assertEqual(self.premier.min_must_sugar_g_l, 189.0)
        self.assertEqual(self.standard.max_total_alcohol_pct, 13.5)
        self.assertEqual(self.premier.max_total_alcohol_pct, 14.0)

        self.assertTrue(
            self.registry.validate_production(
                self.standard, must_sugar_g_l=180.0, potential_alcohol_pct=10.5
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                self.standard, must_sugar_g_l=179.99, potential_alcohol_pct=10.5
            ).eligible
        )
        self.assertTrue(
            self.registry.validate_production(
                self.premier, must_sugar_g_l=189.0, potential_alcohol_pct=11.0
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_release(
                self.standard,
                total_aging_months=12,
                total_alcohol_pct=13.51,
                residual_sugar_g_l=2.0,
                malic_acid_g_l=0.4,
            ).eligible
        )

    def test_exact_elevage_and_release_calendar_is_enforced(self):
        common = dict(
            total_aging_months=12,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=2.0,
            malic_acid_g_l=0.4,
            vintage_year=2026,
        )
        self.assertEqual(
            (self.standard.min_elevage_year_offset, self.standard.min_elevage_until_month, self.standard.min_elevage_until_day),
            (1, 6, 15),
        )
        self.assertEqual(
            (self.standard.release_year_offset, self.standard.earliest_release_month, self.standard.earliest_release_day),
            (1, 6, 30),
        )
        self.assertFalse(
            self.registry.validate_release(
                self.standard,
                elevage_end_year=2027,
                elevage_end_month=6,
                elevage_end_day=14,
                release_year=2027,
                release_month=6,
                release_day=30,
                **common,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_release(
                self.standard,
                elevage_end_year=2027,
                elevage_end_month=6,
                elevage_end_day=15,
                release_year=2027,
                release_month=6,
                release_day=29,
                **common,
            ).eligible
        )
        self.assertTrue(
            self.registry.validate_release(
                self.standard,
                elevage_end_year=2027,
                elevage_end_month=6,
                elevage_end_day=15,
                release_year=2027,
                release_month=6,
                release_day=30,
                **common,
            ).eligible
        )


if __name__ == "__main__":
    unittest.main()
