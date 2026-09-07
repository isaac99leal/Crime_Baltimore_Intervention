import unittest
from scripts.variety_identity_coverage import measure
from sommelier_v2.knowledge.expanded_catalog import VarietyAreaObservation as Observation
from sommelier_v2.knowledge.variety_identity import VarietyIdentityDecision as Decision


class Resolver:
    def resolve(self, name, **scope):
        if name == 'reviewed':
            return Decision('RESOLVED', 'R5', 'vivc:1')
        if name == 'conflict':
            return Decision('CONFLICT', 'R0', candidate_ids=('vivc:1', 'vivc:2'))
        return Decision('UNKNOWN', 'R1')


class IdentityCoverageTests(unittest.TestCase):
    def test_years_and_missing_values_are_not_pooled(self):
        report = measure([Observation('reviewed', area_2000_ha=100, area_2023_ha=20),
                          Observation('unknown', area_2000_ha=100, area_2023_ha=None),
                          Observation('conflict', area_2023_ha=80)], Resolver())
        self.assertEqual(report['area_by_census_year']['2000']['resolved_percent'], 50)
        self.assertEqual(report['area_by_census_year']['2023']['resolved_percent'], 20)
        self.assertEqual(report['area_by_census_year']['2023']['missing_area_rows'], 1)
        self.assertIsNone(report['area_by_census_year']['2010']['resolved_percent'])
        self.assertEqual(report['conflict_count'], 1)
        self.assertEqual(report['conflicts'][0]['generator_policy'], 'block_identity_promotion')
        self.assertEqual(report['level_counts']['R1'], 1)

    def test_thresholds_are_strict_and_duplicate_source_rows_survive(self):
        rows = [Observation('unknown', area_2023_ha=a, source_row=i) for i, a in enumerate((1000, 10000, 10001))]
        report = measure(rows, Resolver())
        self.assertEqual(report['unresolved_over_1000ha_2023'], 2)
        self.assertEqual(report['unresolved_over_10000ha_2023'], 1)
        self.assertEqual(len(report['unresolved_queue']), 3)
