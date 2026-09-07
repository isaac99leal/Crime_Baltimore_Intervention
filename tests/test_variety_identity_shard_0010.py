import unittest
from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry
from scripts.variety_identity_coverage import build_report

EXPECTED = {'Tribidrag': [9703, 'R4'], 'Isabella': [5560, 'R5'], 'Palomino Fino': [8888, 'R5'], 'Fetească Albă': [4119, 'R5'], 'Fetească Regală': [4121, 'R5'], 'Moldova': [7896, 'R5'], 'Fernão Pires': [4100, 'R5'], 'Listán Prieto': [7873, 'R5'], 'Negroamaro': [8456, 'R5'], 'Dimyat': [5716, 'R5'], 'Malvasia Bianca di Candia': [7258, 'R5'], 'Parellada': [8938, 'R5'], 'Bianca': [1321, 'R5'], 'Dornfelder': [3659, 'R5'], 'Loureiro': [6912, 'R5'], 'Corvina Veronese': [2863, 'R5'], 'Pedro Ximénez': [9080, 'R5'], 'Trincadeira': [15685, 'R5'], 'Silvaner': [11805, 'R5'], 'Durif': [3738, 'R5'], 'Tannat': [12257, 'R5'], 'Nebbiolo': [8417, 'R5']}

class Batch4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = VarietyIdentityRegistry()

    def test_reviewed_identities_and_source_boundaries(self):
        for name, (number, level) in EXPECTED.items():
            with self.subTest(name=name):
                d = self.registry.resolve(name, source_id='adelaide_2025')
                self.assertEqual((d.status, d.level, d.canonical_id), ('RESOLVED', level, f'vivc:{number}'))
                self.assertFalse(self.registry.resolve(name, source_id='other-census').identity_confirmed)

    def test_pamid_competing_colors_block_promotion(self):
        d = self.registry.resolve('Pamid', source_id='adelaide_2025')
        self.assertEqual((d.status, d.level), ('CONFLICT', 'R0'))
        self.assertEqual(d.candidate_ids, ('vivc:17323', 'vivc:17324'))
        self.assertIsNone(d.canonical_id)
        self.assertFalse(d.identity_confirmed)

    def test_hybrids_are_not_relabelled_vinifera(self):
        for number in (5560, 7896, 1321):
            self.assertEqual(self.registry.identities[f'vivc:{number}']['species'], 'interspecific cross')

    def test_related_names_do_not_inherit_review(self):
        for name in ('Plavac Mali', 'Pedro Giménez', 'Corvinone', 'Fernão Pires Rosado',
                     'Negroamaro Precoce', 'Malvasia di Candia Aromatica', 'Trincadeira Branca'):
            self.assertFalse(self.registry.resolve(name, source_id='adelaide_2025').identity_confirmed, name)

    def test_coverage_reports_real_conflict(self):
        r = build_report()
        entries = [c for c in r['conflicts'] if c['source_name'] == 'Pamid']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['generator_policy'], 'block_identity_promotion')
        self.assertGreaterEqual(r['level_counts']['R5'], 94)
        self.assertGreaterEqual(r['level_counts']['R4'], 2)
        self.assertGreater(r['area_by_census_year']['2023']['resolved_percent'], 79)
