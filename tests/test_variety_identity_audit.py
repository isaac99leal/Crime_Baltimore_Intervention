from __future__ import annotations

import unittest

from scripts.variety_identity_audit import build_metrics


class VarietyIdentityAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metrics = build_metrics()

    def test_metrics_cover_full_adelaide_prime_table(self):
        self.assertEqual(self.metrics["source_rows"], 1998)
        self.assertEqual(sum(self.metrics["resolution_counts"].values()), 1998)

    def test_current_reviewed_checkpoint_is_at_least_eighty_r5(self):
        self.assertGreaterEqual(self.metrics["resolution_counts"]["R5"], 80)
        self.assertGreaterEqual(self.metrics["resolution_counts"]["R4"], 10)
        self.assertGreater(self.metrics["resolved_2023_pct"], 76.0)

    def test_unresolved_thresholds_are_measured_not_inferred(self):
        unresolved = self.metrics["unresolved_gt_10000_ha"]
        self.assertTrue(unresolved)
        self.assertTrue(
            all(float(row["area_2023_ha"]) > 10000.0 for row in unresolved)
        )
        self.assertGreater(self.metrics["unresolved_gt_1000_ha_count"], 0)

    def test_known_hard_rows_remain_visible(self):
        names = {row["name"] for row in self.metrics["top_unresolved"]}
        self.assertIn("Trebbiano Toscano", names)
        self.assertIn("Alicante Henri Bouschet", names)
        self.assertIn("Côt", names)

    def test_unknown_is_not_counted_as_resolved_area(self):
        self.assertLess(
            self.metrics["resolved_2023_ha"],
            self.metrics["total_2023_ha"],
        )


if __name__ == "__main__":
    unittest.main()
