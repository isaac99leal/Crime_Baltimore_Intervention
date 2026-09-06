from __future__ import annotations

import unittest

from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


class ExactDatePartialValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()
        cls.spec = cls.registry.resolve(
            country="France", appellation="Clos de Vougeot", variant="grand cru"
        )
        if cls.spec is None:
            raise AssertionError("Clos de Vougeot strict specification is missing")

    def release(self, **kwargs):
        defaults = dict(
            total_aging_months=0,
            total_alcohol_pct=13.5,
            residual_sugar_g_l=1.0,
            malic_acid_g_l=0.2,
            vintage_year=2025,
        )
        defaults.update(kwargs)
        return self.registry.validate_release(self.spec, **defaults)

    def test_too_early_release_year_cannot_hide_behind_missing_month_day(self):
        decision = self.release(release_year=2025, require_complete=False)
        self.assertFalse(decision.eligible)
        self.assertTrue(any("Release year must be at least 2026" in issue for issue in decision.issues))

    def test_later_release_year_proves_calendar_compliance_without_month_day(self):
        decision = self.release(release_year=2027, require_complete=False)
        self.assertTrue(decision.eligible, decision.issues)

    def test_same_required_year_without_month_day_is_inconclusive_not_false_in_partial_mode(self):
        decision = self.release(release_year=2026, require_complete=False)
        self.assertTrue(decision.eligible, decision.issues)

    def test_same_required_year_requires_exact_date_in_complete_mode(self):
        decision = self.release(release_year=2026, require_complete=True)
        self.assertFalse(decision.eligible)
        self.assertIn(
            "Exact release month/day is required for complete release-date validation",
            decision.issues,
        )

    def test_invalid_release_calendar_date_is_rejected(self):
        decision = self.release(
            release_year=2026,
            release_month=2,
            release_day=31,
            require_complete=False,
        )
        self.assertFalse(decision.eligible)
        self.assertIn("Release date is not a valid calendar date", decision.issues)

    def test_release_boundary_is_exact(self):
        early = self.release(
            release_year=2026, release_month=6, release_day=29, require_complete=False
        )
        boundary = self.release(
            release_year=2026, release_month=6, release_day=30, require_complete=False
        )
        self.assertFalse(early.eligible)
        self.assertTrue(boundary.eligible, boundary.issues)

    def test_too_early_elevage_year_cannot_hide_behind_missing_month_day(self):
        decision = self.release(
            elevage_end_year=2025,
            release_year=2027,
            require_complete=False,
        )
        self.assertFalse(decision.eligible)
        self.assertTrue(any("Elevage must continue through 2026-06-15" in issue for issue in decision.issues))

    def test_invalid_elevage_calendar_date_is_rejected(self):
        decision = self.release(
            elevage_end_year=2026,
            elevage_end_month=2,
            elevage_end_day=31,
            release_year=2027,
            require_complete=False,
        )
        self.assertFalse(decision.eligible)
        self.assertIn("Elevage end date is not a valid calendar date", decision.issues)

    def test_elevage_boundary_is_exact(self):
        early = self.release(
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=14,
            release_year=2027,
            require_complete=False,
        )
        boundary = self.release(
            elevage_end_year=2026,
            elevage_end_month=6,
            elevage_end_day=15,
            release_year=2027,
            require_complete=False,
        )
        self.assertFalse(early.eligible)
        self.assertTrue(boundary.eligible, boundary.issues)


if __name__ == "__main__":
    unittest.main()
