from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sommelier_v2.knowledge.legal_sources import LegalSourceRegistry


class LegalSourceRegistryTests(unittest.TestCase):
    def test_missing_source_index_is_safe_and_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = LegalSourceRegistry(Path(tmp) / "missing.json")
            self.assertEqual(registry.records, [])
            self.assertEqual(registry.stats()["legal_source_records"], 0)

    def test_document_index_is_provenance_not_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            path.write_text(json.dumps([{
                "gi_identifier": "EUGI00000000001",
                "file_number": "PDO-XX-A0001",
                "protected_names": ["Strict Example"],
                "countries": ["XX"],
                "gi_type": "PDO",
                "status": "registered",
                "modification_date": "2026-01-01T00:00:00Z",
                "application_id": "123",
                "product_specification_attachment_ids": ["456"],
                "single_document_attachment_ids": ["789"],
                "source_urls": ["https://example.invalid/456", "https://example.invalid/789"],
                "index_status": "product_specification_indexed",
            }]), encoding="utf-8")
            registry = LegalSourceRegistry(path)
            record = registry.by_gi_identifier("EUGI00000000001")
            self.assertIsNotNone(record)
            self.assertTrue(record.has_product_specification)
            self.assertTrue(record.has_authoritative_document)
            self.assertEqual(registry.find("Strict Example", country_code="XX"), (record,))
            self.assertEqual(registry.stats()["legal_sources_with_product_specification"], 1)


if __name__ == "__main__":
    unittest.main()
