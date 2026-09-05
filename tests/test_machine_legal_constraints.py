from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path

from sommelier_v2.knowledge.legal_rules import LegalAwareRegionGrapeRulebook
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.machine_legal_constraints import MachineLegalConstraintRegistry


@dataclass
class Grape:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)


class Catalog:
    def __init__(self):
        self._grapes = [Grape("g:allowed", "Allowed"), Grape("g:forbidden", "Forbidden")]
        self.commercial_observations = []

    @staticmethod
    def norm(value):
        return "".join(ch.lower() for ch in value if ch.isalnum())

    def grape(self, name):
        key = self.norm(name)
        for grape in self._grapes:
            if key in {self.norm(grape.name), *(self.norm(a) for a in grape.aliases)}:
                return grape
        return None

    def area_for(self, name, country=None):
        return []


class MachineConstraintSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        regions = root / "regions.json"
        regions.write_text(json.dumps({"regions": [{
            "country": "XX",
            "wine_regions": [{
                "name": "Example Region",
                "primary_grapes": ["Allowed"],
                "sub_regions": [{
                    "name": "Example Sub",
                    "primary_grapes": ["Allowed"],
                    "communes": [{"name": "Example GI", "primary_grapes": ["Allowed"], "allowed_grapes": []}],
                }],
            }],
        }]}), encoding="utf-8")
        machine_path = root / "machine.json"
        machine_path.write_text(json.dumps([{
            "gi_identifier": "EUGI00000000001",
            "file_number": "PDO-XX-A0001",
            "protected_names": ["Example GI"],
            "countries": ["XX"],
            "gi_type": "PDO",
            "allowed_grapes": ["Allowed"],
            "constraint_level": "deny_only",
            "extraction_status": "explicit_variety_section_extracted",
            "source_attachment_id": "123",
            "source_url": "https://example.invalid/123",
            "section_sha256": "abc",
        }]), encoding="utf-8")
        specs_path = root / "specs.json"
        specs_path.write_text(json.dumps({"sources": {}, "specs": []}), encoding="utf-8")
        self.rules = LegalAwareRegionGrapeRulebook(
            regions,
            catalog=Catalog(),
            legal_specs=LegalSpecRegistry(specs_path),
            machine_constraints=MachineLegalConstraintRegistry(machine_path),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_machine_constraint_can_reject_outsider(self):
        decision = self.rules.evaluate(
            country="XX", region="Example Region", appellation="Example GI",
            grapes={"Forbidden": 100}, label_scope="regulated_gi",
        )
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.status, "grape_not_permitted_machine_extracted")

    def test_machine_membership_pass_does_not_authorize_gi(self):
        decision = self.rules.evaluate(
            country="XX", region="Example Region", appellation="Example GI",
            grapes={"Allowed": 100}, label_scope="regulated_gi",
        )
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.status, "legal_grape_rule_unverified")


if __name__ == "__main__":
    unittest.main()
