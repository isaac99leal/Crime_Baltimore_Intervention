from __future__ import annotations

import unittest

from sommelier_v2.knowledge.process_chemistry_evidence import (
    MODEL_EVIDENCE_LINKS,
    ProcessChemistryEvidenceError,
    ProcessChemistryEvidenceRegistry,
)


class ProcessChemistryEvidenceRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = ProcessChemistryEvidenceRegistry()

    def test_recovered_chemistry_corpus_scale(self):
        stats = self.registry.stats()
        self.assertEqual(stats.source_count, 19)
        self.assertEqual(stats.referenced_source_count, 16)
        self.assertEqual(stats.record_count, 28)
        self.assertGreaterEqual(stats.domain_count, 10)
        self.assertEqual(stats.record_with_measurements_count, 13)
        self.assertEqual(stats.record_with_conditions_count, 4)

    def test_every_record_source_reference_resolves(self):
        for record in self.registry.records:
            self.assertEqual(record.fact_type, "source-backed")
            self.assertTrue(record.source_refs)
            for source_ref in record.source_refs:
                source = self.registry.source(source_ref)
                self.assertIsNotNone(source)
                assert source is not None
                self.assertTrue(source.url.startswith(("https://", "http://")))

    def test_measurements_and_conditions_are_immutable(self):
        yan = self.registry.record("chem-yan-definition")
        self.assertIsNotNone(yan)
        assert yan is not None
        with self.assertRaises(TypeError):
            yan.measurements["invented"] = 999  # type: ignore[index]

        smoke = self.registry.record("chem-smoke-risk-pinot-noir")
        self.assertIsNotNone(smoke)
        assert smoke is not None
        with self.assertRaises(TypeError):
            smoke.conditions["cultivar"] = "Merlot"  # type: ignore[index]
        with self.assertRaises(TypeError):
            smoke.measurements["moderateHighRiskUgKg"]["guaiacol"] = (999, 999)  # type: ignore[index]

    def test_source_backed_numbers_are_not_hidden_coefficients(self):
        with self.assertRaises(ProcessChemistryEvidenceError):
            self.registry.assert_not_simulation_coefficient(
                "chem-white-juice-solids-turbidity",
                "studyCompromiseNtu",
            )
        with self.assertRaises(ProcessChemistryEvidenceError):
            self.registry.assert_not_simulation_coefficient(
                "chem-brett-risk-window",
                "molecularSo2GuideMgLForBrettControl",
            )

    def test_model_evidence_links_resolve_and_state_scope(self):
        self.assertGreaterEqual(len(MODEL_EVIDENCE_LINKS), 6)
        for link in MODEL_EVIDENCE_LINKS:
            records = self.registry.model_evidence(link.model_element)
            self.assertEqual(len(records), len(link.record_ids))
            self.assertTrue(self.registry.model_evidence_note(link.model_element))
            self.assertTrue(all(record.id in link.record_ids for record in records))

        solids = self.registry.model_evidence(
            "fermentation_chemistry.white_juice_solids_risk"
        )
        self.assertEqual([record.id for record in solids], ["chem-white-juice-solids-turbidity"])
        self.assertIn(
            "derived",
            (self.registry.model_evidence_note(
                "fermentation_chemistry.white_juice_solids_risk"
            ) or "").lower(),
        )

    def test_domain_query_preserves_distinct_fault_and_stability_records(self):
        fault = self.registry.by_domain("fault-risk")
        self.assertEqual(
            {record.id for record in fault},
            {"chem-volatile-acidity", "chem-ethyl-acetate"},
        )
        stability = self.registry.by_domain("stability")
        self.assertEqual(
            {record.id for record in stability},
            {
                "chem-ph-stability",
                "chem-tartrate-stability",
                "chem-cold-stability-not-sensory-fault",
                "chem-so2-ph-effectiveness",
            },
        )

    def test_smoke_thresholds_remain_cultivar_specific(self):
        pinot = self.registry.record("chem-smoke-risk-pinot-noir")
        chardonnay = self.registry.record("chem-smoke-risk-chardonnay")
        shiraz = self.registry.record("chem-smoke-risk-shiraz")
        assert pinot is not None and chardonnay is not None and shiraz is not None
        self.assertEqual(pinot.condition("cultivar"), "Pinot Noir")
        self.assertEqual(chardonnay.condition("cultivar"), "Chardonnay")
        self.assertEqual(shiraz.condition("cultivar"), "Shiraz")
        self.assertNotEqual(
            pinot.measurement("moderateHighRiskUgKg"),
            chardonnay.measurement("moderateHighRiskUgKg"),
        )

    def test_tartrate_record_does_not_call_crystals_microbiological_spoilage(self):
        record = self.registry.record("chem-cold-stability-not-sensory-fault")
        self.assertIsNotNone(record)
        assert record is not None
        text = " ".join(record.facts).lower()
        self.assertIn("physical stability", text)
        self.assertIn("must not automatically be scored", text)


if __name__ == "__main__":
    unittest.main()
