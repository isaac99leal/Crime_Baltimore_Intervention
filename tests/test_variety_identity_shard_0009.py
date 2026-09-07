import unittest
from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry
from scripts.variety_identity_coverage import build_report

EXPECTED = {'Côt': 2889, 'Muscat Blanc à Petits Grains': 8193,
            'Muscat of Alexandria': 8241, 'Verdejo': 12949, 'Pinot Meunier': 9278,
            'Müller-Thurgau': 8141, 'Sémillon': 11480, 'Trebbiano Romagnolo': 12625,
            'Muscat Ottonel': 8243, 'Garganega': 4419}


class Batch3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_reviewed_source_names_resolve(self):
        for name, number in EXPECTED.items():
            with self.subTest(name=name):
                d = self.registry.resolve(name, source_id='adelaide_2025')
                self.assertEqual((d.status, d.level, d.canonical_id), ('RESOLVED', 'R5', f'vivc:{number}'))
                self.assertFalse(self.registry.resolve(name, source_id='another-census').identity_confirmed)

    def test_cot_review_supersedes_candidate_without_merging_other_names(self):
        d = self.registry.resolve('Côt', source_id='adelaide_2025')
        self.assertEqual(d.canonical_id, 'vivc:2889')
        self.assertIn('astra-batch2-2889-2026-09-07', d.evidence_ids)
        self.assertIn('astra-batch3-2889-2026-09-07', d.evidence_ids)
        for name in ('Cabernet Malbec', 'Malbec argenté', 'Auxerrois'):
            self.assertFalse(self.registry.resolve(name, source_id='adelaide_2025').identity_confirmed)

    def test_families_keep_separate_authority_ids(self):
        for names in [('Muscat Blanc à Petits Grains', 'Muscat of Alexandria', 'Muscat Ottonel'),
                      ('Pinot Noir', 'Pinot Meunier'), ('Trebbiano Toscano', 'Trebbiano Romagnolo')]:
            ids = {self.registry.resolve(n, source_id='adelaide_2025').canonical_id for n in names}
            self.assertNotIn(None, ids)
            self.assertEqual(len(ids), len(names))
        for name in ('Muscat', 'Muscat à Petits Grains Rouges', 'Catarratto Bianco'):
            self.assertFalse(self.registry.resolve(name, source_id='adelaide_2025').identity_confirmed)

    def test_area_coverage_includes_reviewed_cot(self):
        report = build_report()
        self.assertGreaterEqual(report['level_counts']['R5'], 73)
        self.assertGreater(report['area_by_census_year']['2023']['resolved_percent'], 73)
        self.assertNotIn('Côt', [r['observation']['prime_name'] for r in report['unresolved_queue']])
