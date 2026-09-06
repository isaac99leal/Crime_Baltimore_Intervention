from __future__ import annotations

import unittest

from sommelier_v2.knowledge import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.vineyard_legal_constraints import VineyardLegalConstraintRegistry
from sommelier_v2.knowledge.vineyard_yield_adjustments import VineyardYieldAdjustmentRegistry


class GevreyLegalEnrichmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = LegalSpecRegistry()

    def spec(self, variant: str):
        spec = self.registry.resolve(
            country="France",
            appellation="Gevrey-Chambertin",
            variant=variant,
        )
        self.assertIsNotNone(spec)
        return spec

    def test_existing_ids_are_enriched_not_duplicated(self) -> None:
        ids = [spec.id for spec in self.registry.specs]
        self.assertEqual(ids.count("fr:gevrey-chambertin:standard"), 1)
        self.assertEqual(ids.count("fr:gevrey-chambertin:premier-cru"), 1)
        self.assertIn(
            "fr:gevrey-chambertin:standard:masa-2011-enrichment",
            self.registry.applied_amendment_ids,
        )
        self.assertIn(
            "fr:gevrey-chambertin:premier-cru:masa-2011-enrichment",
            self.registry.applied_amendment_ids,
        )

    def test_exact_village_and_pc_fields_are_executable(self) -> None:
        village = self.spec("standard")
        premier = self.spec("premier cru")
        self.assertEqual(
            (
                village.min_must_sugar_g_l,
                village.min_potential_alcohol_pct,
                village.max_yield_hl_ha,
                village.max_total_alcohol_pct,
            ),
            (180.0, 10.5, 50.0, 13.5),
        )
        self.assertEqual(
            (
                premier.min_must_sugar_g_l,
                premier.min_potential_alcohol_pct,
                premier.max_yield_hl_ha,
                premier.max_total_alcohol_pct,
            ),
            (189.0, 11.0, 48.0, 14.0),
        )
        for spec in (village, premier):
            self.assertEqual(
                (spec.min_elevage_year_offset, spec.min_elevage_until_month, spec.min_elevage_until_day),
                (1, 6, 15),
            )
            self.assertEqual(
                (spec.release_year_offset, spec.earliest_release_month, spec.earliest_release_day),
                (1, 6, 30),
            )

    def test_pc_maturity_total_alcohol_and_calendar_boundaries(self) -> None:
        spec = self.spec("premier cru")
        self.assertTrue(
            self.registry.validate_production(
                spec,
                wine_yield_hl_ha=48.0,
                must_sugar_g_l=189.0,
                potential_alcohol_pct=11.0,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                spec,
                wine_yield_hl_ha=48.0,
                must_sugar_g_l=188.99,
                potential_alcohol_pct=11.0,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_release(
                spec,
                total_aging_months=0,
                total_alcohol_pct=14.01,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_release(
                spec,
                total_aging_months=0,
                vintage_year=2025,
                elevage_end_year=2026,
                elevage_end_month=6,
                elevage_end_day=14,
                release_year=2026,
                release_month=6,
                release_day=30,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_release(
                spec,
                total_aging_months=0,
                vintage_year=2025,
                elevage_end_year=2026,
                elevage_end_month=6,
                elevage_end_day=15,
                release_year=2026,
                release_month=6,
                release_day=29,
            ).eligible
        )

    def test_existing_26_pc_climat_identities_remain_intact(self) -> None:
        catalog = WorldWineKnowledgeCatalog()
        climats = {
            site.name
            for site in catalog.named_sites
            if site.parent == "Gevrey-Chambertin"
            and site.site_type == "climat"
            and site.classification == "Premier Cru"
        }
        self.assertEqual(len(climats), 26)
        self.assertIn("Clos Saint-Jacques", climats)
        self.assertIn("Les Cazetiers", climats)
        self.assertIn("Aux Combottes", climats)


class GevreyVineyardLawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = VineyardLegalConstraintRegistry()
        cls.yields = VineyardYieldAdjustmentRegistry()

    @staticmethod
    def valid_inputs() -> dict[str, object]:
        return {
            "country": "France",
            "appellation": "Gevrey-Chambertin",
            "wine_style": "red",
            "vine_density_per_ha": 9000,
            "irrigation_mm_per_week": 0.0,
            "planting_pattern": "rows",
            "row_spacing_m": 1.25,
            "vine_spacing_m": 0.50,
            "pruning_system": "guyot_simple",
            "retained_buds_per_vine": 8,
            "fruiting_shoots_per_vine": 8,
            "support_system": "trellis",
            "canopy_height_m": 0.75,
            "parcel_crop_load_kg_ha": 9000.0,
        }

    def test_complete_boundary_path_passes(self) -> None:
        assessment = self.registry.assess(**self.valid_inputs())
        self.assertIs(assessment.satisfied, True)
        self.assertIn("source:gevrey_masa_2011_current", assessment.evidence)

    def test_density_irrigation_pruning_and_crop_load_violations_fail(self) -> None:
        for field, value in (
            ("vine_density_per_ha", 8999),
            ("irrigation_mm_per_week", 0.01),
            ("retained_buds_per_vine", 9),
            ("parcel_crop_load_kg_ha", 9000.01),
        ):
            values = self.valid_inputs()
            values[field] = value
            if field == "retained_buds_per_vine":
                values["fruiting_shoots_per_vine"] = 9
            self.assertIs(self.registry.assess(**values).satisfied, False)

    def test_extra_retained_bud_is_allowed_when_observed_fruiting_shoots_comply(self) -> None:
        values = self.valid_inputs()
        values["retained_buds_per_vine"] = 9
        values["fruiting_shoots_per_vine"] = 8
        self.assertIs(self.registry.assess(**values).satisfied, True)

    def test_foule_half_meter_boundary_is_strict(self) -> None:
        values = self.valid_inputs()
        values.update(
            planting_pattern="foule",
            row_spacing_m=None,
            vine_spacing_m=0.50,
            support_system="stake",
            canopy_height_m=None,
        )
        self.assertIs(self.registry.assess(**values).satisfied, False)
        values["vine_spacing_m"] = 0.51
        self.assertIs(self.registry.assess(**values).satisfied, True)

    def test_dead_vine_threshold_uses_d645_4_multiplier(self) -> None:
        at_threshold = self.yields.assess(
            country="France",
            appellation="Gevrey-Chambertin",
            dead_missing_vine_fraction=0.20,
        )
        above = self.yields.assess(
            country="France",
            appellation="Gevrey-Chambertin",
            dead_missing_vine_fraction=0.25,
        )
        self.assertEqual(at_threshold.multiplier, 1.0)
        self.assertAlmostEqual(above.multiplier, 0.75)
        self.assertIn("threshold-source:gevrey_masa_2011_current", above.evidence)
        self.assertIn("remedy-source:fr_code_rural_d645_4", above.evidence)


if __name__ == "__main__":
    unittest.main()
