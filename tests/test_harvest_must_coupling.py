from __future__ import annotations

import unittest
from types import SimpleNamespace

from sommelier_v2.knowledge.harvest_must import (
    HarvestMustConstraintError,
    HarvestMustPlan,
    must_from_vineyard,
)


def outcome(**changes):
    vintage = SimpleNamespace(
        botrytis_pressure=0.12,
        disease_pressure=0.10,
        heterogeneity_index=0.18,
        extreme_heat_days=1,
        harvest_window_rain_mm=20.0,
        concentration_index=0.72,
        tannin_quality_index=0.68,
        phenolic_ripeness_index=0.74,
    )
    values = dict(
        block_id="b:test",
        grape="Pinot Noir",
        total_grape_tonnes=8.0,
        potential_alcohol_pct=13.0,
        ph=3.42,
        titratable_acidity_g_l=6.4,
        malic_acid_g_l=2.4,
        disease_loss_fraction=0.08,
        rot_loss_fraction=0.06,
        harvestable=True,
        label_eligible=True,
        vintage=vintage,
    )
    values.update(changes)
    return SimpleNamespace(**values)


class HarvestMustCouplingTests(unittest.TestCase):
    def test_measured_harvest_chemistry_becomes_must(self):
        source = outcome()
        profile = must_from_vineyard(
            source,
            HarvestMustPlan(
                measured_yan_mg_l=175.0,
                juice_yield_l_per_tonne=680.0,
                sorting_intensity=0.50,
                clarification_loss_fraction=0.03,
                must_temp_c=16.0,
            ),
        )
        self.assertEqual(profile.yan_source, "measured")
        self.assertAlmostEqual(profile.must.yan_mg_l, 175.0)
        self.assertAlmostEqual(profile.must.ph, source.ph)
        self.assertAlmostEqual(profile.must.titratable_acidity_g_l, source.titratable_acidity_g_l)
        self.assertAlmostEqual(profile.must.malic_acid_g_l, source.malic_acid_g_l)
        self.assertAlmostEqual(profile.must.sugar_g_l, 13.0 * 16.83, places=6)
        self.assertLess(profile.usable_tonnes, source.total_grape_tonnes)
        self.assertLess(profile.must_volume_l, source.total_grape_tonnes * 680.0)
        self.assertGreater(profile.fruit_integrity_index, 0.0)

    def test_yan_is_never_silently_invented(self):
        with self.assertRaises(HarvestMustConstraintError):
            must_from_vineyard(outcome(), HarvestMustPlan())

        profile = must_from_vineyard(
            outcome(), HarvestMustPlan(fallback_yan_mg_l=140.0)
        )
        self.assertEqual(profile.yan_source, "explicit_prior")
        self.assertTrue(any("prior" in warning.lower() for warning in profile.warnings))

    def test_compromised_harvest_requires_explicit_override(self):
        bad = outcome(harvestable=False)
        with self.assertRaises(HarvestMustConstraintError):
            must_from_vineyard(bad, HarvestMustPlan(measured_yan_mg_l=160.0))

        profile = must_from_vineyard(
            bad,
            HarvestMustPlan(
                measured_yan_mg_l=160.0,
                allow_compromised_harvest=True,
            ),
        )
        self.assertTrue(any("compromised" in warning.lower() for warning in profile.warnings))

    def test_worse_harvest_condition_propagates_to_cellar_risk(self):
        clean = outcome()
        dirty_vintage = SimpleNamespace(
            botrytis_pressure=0.90,
            disease_pressure=0.85,
            heterogeneity_index=0.75,
            extreme_heat_days=9,
            harvest_window_rain_mm=105.0,
            concentration_index=0.62,
            tannin_quality_index=0.48,
            phenolic_ripeness_index=0.55,
        )
        dirty = outcome(
            disease_loss_fraction=0.55,
            rot_loss_fraction=0.60,
            vintage=dirty_vintage,
        )
        plan = HarvestMustPlan(measured_yan_mg_l=180.0, sorting_intensity=0.35)
        clean_profile = must_from_vineyard(clean, plan)
        dirty_profile = must_from_vineyard(dirty, plan)

        self.assertGreater(dirty_profile.sorting_loss_fraction, clean_profile.sorting_loss_fraction)
        self.assertGreater(dirty_profile.retained_rot_fraction, clean_profile.retained_rot_fraction)
        self.assertGreater(dirty_profile.microbial_risk_index, clean_profile.microbial_risk_index)
        self.assertGreater(dirty_profile.oxidation_risk_index, clean_profile.oxidation_risk_index)
        self.assertLess(dirty_profile.fruit_integrity_index, clean_profile.fruit_integrity_index)
        self.assertLess(dirty_profile.extraction_potential_index, clean_profile.extraction_potential_index)

    def test_label_failure_does_not_destroy_physical_fruit(self):
        profile = must_from_vineyard(
            outcome(label_eligible=False),
            HarvestMustPlan(measured_yan_mg_l=170.0),
        )
        self.assertGreater(profile.must.volume_l, 0.0)
        self.assertTrue(any("protected-origin" in warning.lower() for warning in profile.warnings))


if __name__ == "__main__":
    unittest.main()
