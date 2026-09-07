import unittest
from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry
from scripts.variety_identity_coverage import build_report


class VarietyIdentityShard0008Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_reviewed_literal_rows_and_synonym_level(self):
        for name, number, level in [('Trebbiano Toscano', 12628, 'R5'),
                                    ('Alicante Henri Bouschet', 304, 'R5'),
                                    ('Prosecco', 9741, 'R5'), ('Mazuelo', 2098, 'R4')]:
            with self.subTest(name=name):
                result = self.registry.resolve(name, source_id='adelaide_2025')
                self.assertTrue(result.identity_confirmed)
                self.assertEqual((result.canonical_id, result.level), (f'vivc:{number}', level))
                self.assertEqual(self.registry.resolve(name, source_id='unreviewed-census').status, 'UNKNOWN')

    def test_related_names_and_aggregates_are_not_promoted(self):
        for name in ('Trebbiano', 'Trebbiano Romagnolo', 'Biancame', 'Ugni Blanc',
                     'Alicante Bouschet', 'Prosecco lungo', 'Glera', 'Mazuela',
                     'Carignan', 'other', 'other red', 'other white'):
            with self.subTest(name=name):
                result = self.registry.resolve(name, source_id='adelaide_2025')
                self.assertFalse(result.identity_confirmed)
                self.assertIsNone(result.canonical_id)

    def test_circumflex_requires_evidence(self):
        for name in ('Côt', 'Cot'):
            result = self.registry.resolve(name, source_id='adelaide_2025')
            self.assertEqual((result.status, result.level), ('CANDIDATE', 'R2'))
            self.assertEqual(result.candidate_ids, ('vivc:2889',))
            self.assertIsNone(result.canonical_id)

    def test_coverage_counts_confirmed_synonym_but_not_candidate(self):
        report = build_report()
        self.assertGreaterEqual(report['level_counts']['R5'], 63)
        self.assertGreaterEqual(report['level_counts']['R4'], 1)
        self.assertGreaterEqual(report['level_counts']['R2'], 1)
        self.assertEqual(report['source_rows'], 1998)
        self.assertGreater(report['area_by_census_year']['2023']['resolved_percent'], 68)
        self.assertIn('sommelier_v2/knowledge/data/variety_identity_evidence_shard_0008.json', report['input_sha256'])
