from __future__ import annotations

import unittest
import csv
import tempfile
from pathlib import Path

from scripts.variety_identity_audit import build_metrics


class VarietyIdentityAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metrics = build_metrics()

    def test_metrics_cover_full_adelaide_prime_table(self):
        self.assertEqual(self.metrics["source_rows"], 1998)
        self.assertEqual(sum(self.metrics["resolution_counts"].values()), 1998)

    def test_current_reviewed_checkpoint_is_at_least_eighty_r5(self):
        self.assertGreaterEqual(self.metrics["resolution_counts"]["R5"], 85)
        self.assertGreaterEqual(self.metrics["resolution_counts"]["R4"], 20)
        self.assertGreater(self.metrics["resolved_2023_pct"], 79.0)
        self.assertGreaterEqual(self.metrics["resolution_counts"]["R0"], 3)
        self.assertGreaterEqual(self.metrics["resolution_counts"]["R3"], 4)

    def test_unresolved_thresholds_are_measured_not_inferred(self):
        unresolved = self.metrics["unresolved_gt_10000_ha"]
        self.assertTrue(unresolved)
        self.assertTrue(
            all(float(row["area_2023_ha"]) > 10000.0 for row in unresolved)
        )
        self.assertGreater(self.metrics["unresolved_gt_1000_ha_count"], 0)

    def test_known_hard_rows_remain_visible(self):
        names = {row["name"] for row in self.metrics["top_unresolved"]}
        self.assertNotIn("Trebbiano Toscano", names)
        self.assertNotIn("Alicante Henri Bouschet", names)
        self.assertNotIn("Côt", names)
        self.assertNotIn("Tribidrag", names)
        self.assertIn("Catarratto Bianco", names)
        self.assertIn("Criolla Grande", names)

    def test_unknown_is_not_counted_as_resolved_area(self):
        self.assertLess(
            self.metrics["resolved_2023_ha"],
            self.metrics["total_2023_ha"],
        )


class IdentityAuditTests(unittest.TestCase):
    def test_aggregate_queue_exclusion_preserves_census_area(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'census.csv'
            with path.open('w', newline='') as handle:
                writer = csv.writer(handle)
                writer.writerow(['prime', 'area_2000_ha', 'area_2010_ha', 'area_2016_ha', 'area_2023_ha'])
                writer.writerows([
                    ['Other', 0, 0, 0, 30000],
                    ['Other red', 0, 0, 0, 20000],
                    ['Other white', 0, 0, 0, 10000],
                    ['Other Test Grape', 0, 0, 0, 15000],
                    ['Unreviewed Test Grape', 0, 0, 0, 2000],
                ])
            metrics = build_metrics(path)
        self.assertEqual(metrics['total_2023_ha'], 77000)
        self.assertEqual(metrics['aggregate_category_rows'], 3)
        self.assertEqual(metrics['aggregate_category_2023_ha'], 60000)
        self.assertEqual(metrics['named_rows_2023_ha'], 17000)
        self.assertEqual(metrics['named_unresolved_gt_1000_ha_count'], 2)
        self.assertEqual([r['name'] for r in metrics['named_unresolved_gt_10000_ha']], ['Other Test Grape'])
        self.assertEqual(len(metrics['unresolved_gt_10000_ha']), 3)


if __name__ == "__main__":
    unittest.main()
