from __future__ import annotations

import unittest

from sommelier_v2.knowledge import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory
from sommelier_v2.knowledge.vineyard_legal_constraints import VineyardLegalConstraintRegistry
from sommelier_v2.knowledge.vineyard_yield_adjustments import VineyardYieldAdjustmentRegistry


PRINCIPAL_CLIMATS = {
    "Champs Perdrix",
    "Le Clos",
    "Aux Genelières",
    "Au Champ Salomon",
    "Les Favières",
    "Le Clos de Jeu",
    "Les Grasses Têtes",
    "Le Boivin",
    "La Charme aux Prêtres",
    "Les Échezots",
    "Les Longeroies",
    "Clos du Roy",
    "Les Récilles",
    "Les Vignes Marie",
    "Saint-Jacques",
    "Le Chapitre",
}


class MarsannaySiteIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = WorldWineKnowledgeCatalog()
        cls.rows = [site for site in cls.catalog.named_sites if site.parent == "Marsannay"]

    def test_bivb_principal_climats_are_present_as_real_identities(self) -> None:
        rows = [site for site in self.rows if site.site_type == "climat"]
        self.assertEqual({site.name for site in rows}, PRINCIPAL_CLIMATS)
        self.assertEqual(len(rows), 16)
        for site in rows:
            self.assertEqual(site.legal_status, "documented_named_site")
            self.assertIn("bivb_marsannay_current", site.source_ids)

    def test_named_site_identity_does_not_create_label_authority(self) -> None:
        site = next(site for site in self.rows if site.name == "Les Longeroies")
        factory = WineOriginFactory(catalog=self.catalog)
        origin = factory.create(
            OriginRequest(
                country="France",
                region="Bourgogne",
                appellation="Marsannay",
                grapes={"Pinot Noir": 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant="red standard",
            )
        )
        self.assertFalse(origin.site_claim_eligible)
        self.assertEqual(origin.site_claim_status, "site_claim_rule_unverified")


class MarsannayLegalMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = LegalSpecRegistry()

    def spec(self, variant: str):
        spec = self.registry.resolve(
            country="France",
            appellation="Marsannay",
            variant=variant,
        )
        self.assertIsNotNone(spec)
        return spec

    def test_three_color_paths_resolve_with_exact_maturity_and_yield(self) -> None:
        expected = {
            "white standard": (178.0, 11.0, 57.0, 13.5, 3.0),
            "red standard": (180.0, 10.5, 50.0, 13.5, 2.0),
            "rose standard": (180.0, 10.5, 60.0, 13.0, 3.0),
        }
        for variant, values in expected.items():
            spec = self.spec(variant)
            actual = (
                spec.min_must_sugar_g_l,
                spec.min_potential_alcohol_pct,
                spec.max_yield_hl_ha,
                spec.max_total_alcohol_pct,
                spec.max_residual_sugar_g_l,
            )
            self.assertEqual(actual, values)

    def test_white_pinot_gris_blend_cap_is_executable(self) -> None:
        spec = self.spec("white standard")
        self.assertTrue(
            self.registry.evaluate_blend(
                spec,
                {"Chardonnay": 70, "Pinot Gris": 30},
            ).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(
                spec,
                {"Chardonnay": 69, "Pinot Gris": 31},
            ).eligible
        )

    def test_red_accessories_are_not_overauthorized_by_per_grape_limits(self) -> None:
        spec = self.spec("red standard")
        self.assertTrue(self.registry.evaluate_blend(spec, "Pinot Noir").eligible)
        for accessory in ("Chardonnay", "Pinot Blanc", "Pinot Gris"):
            self.assertFalse(
                self.registry.evaluate_blend(
                    spec,
                    {"Pinot Noir": 95, accessory: 5},
                ).eligible
            )

    def test_rose_positive_path_keeps_principal_varieties_only(self) -> None:
        spec = self.spec("rose standard")
        self.assertTrue(self.registry.evaluate_blend(spec, "Pinot Noir").eligible)
        self.assertTrue(self.registry.evaluate_blend(spec, "Pinot Gris").eligible)
        self.assertTrue(
            self.registry.evaluate_blend(
                spec,
                {"Pinot Noir": 60, "Pinot Gris": 40},
            ).eligible
        )
        self.assertFalse(
            self.registry.evaluate_blend(
                spec,
                {"Pinot Noir": 90, "Chardonnay": 10},
            ).eligible
        )

    def test_maturity_yield_and_total_alcohol_boundaries_execute(self) -> None:
        red = self.spec("red standard")
        self.assertTrue(
            self.registry.validate_production(
                red,
                wine_yield_hl_ha=50.0,
                must_sugar_g_l=180.0,
                potential_alcohol_pct=10.5,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                red,
                wine_yield_hl_ha=50.01,
                must_sugar_g_l=180.0,
                potential_alcohol_pct=10.5,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                red,
                wine_yield_hl_ha=50.0,
                must_sugar_g_l=179.99,
                potential_alcohol_pct=10.5,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_release(
                red,
                total_aging_months=0,
                total_alcohol_pct=13.51,
            ).eligible
        )

    def test_red_malic_and_color_specific_sugar_limits_execute(self) -> None:
        red = self.spec("red standard")
        self.assertEqual(red.max_malic_acid_g_l, 0.4)
        self.assertFalse(
            self.registry.validate_release(
                red,
                total_aging_months=0,
                residual_sugar_g_l=2.01,
                malic_acid_g_l=0.4,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_release(
                red,
                total_aging_months=0,
                residual_sugar_g_l=2.0,
                malic_acid_g_l=0.41,
            ).eligible
        )

    def test_white_and_red_exact_calendar_but_not_rose_is_encoded(self) -> None:
        for variant in ("white standard", "red standard"):
            spec = self.spec(variant)
            self.assertEqual(
                (spec.min_elevage_year_offset, spec.min_elevage_until_month, spec.min_elevage_until_day),
                (1, 6, 15),
            )
            self.assertEqual(
                (spec.release_year_offset, spec.earliest_release_month, spec.earliest_release_day),
                (1, 6, 30),
            )
            early = self.registry.validate_release(
                spec,
                total_aging_months=0,
                vintage_year=2025,
                elevage_end_year=2026,
                elevage_end_month=6,
                elevage_end_day=15,
                release_year=2026,
                release_month=6,
                release_day=29,
            )
            self.assertFalse(early.eligible)

        rose = self.spec("rose standard")
        self.assertIsNone(rose.min_elevage_until_month)
        self.assertIsNone(rose.release_year_offset)
        self.assertIsNone(rose.earliest_release_month)


class MarsannayVineyardLawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = VineyardLegalConstraintRegistry()
        cls.yields = VineyardYieldAdjustmentRegistry()

    @staticmethod
    def valid_inputs(style: str = "red") -> dict[str, object]:
        return {
            "country": "France",
            "appellation": "Marsannay",
            "wine_style": style,
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
            "parcel_crop_load_kg_ha": 9000.0 if style == "red" else 10500.0,
        }

    def test_complete_red_white_and_rose_paths_pass(self) -> None:
        for style in ("red", "white", "rose"):
            assessment = self.registry.assess(**self.valid_inputs(style))
            self.assertIs(assessment.satisfied, True)
            self.assertIn("source:marsannay_masa_2020_cdc", assessment.evidence)

    def test_white_cordon_allows_ten_buds_but_red_does_not(self) -> None:
        white = self.valid_inputs("white")
        white.update(pruning_system="cordon_royat", retained_buds_per_vine=10, fruiting_shoots_per_vine=10)
        self.assertIs(self.registry.assess(**white).satisfied, True)

        red = self.valid_inputs("red")
        red.update(pruning_system="cordon_royat", retained_buds_per_vine=10, fruiting_shoots_per_vine=10)
        self.assertIs(self.registry.assess(**red).satisfied, False)

    def test_geometry_irrigation_and_crop_load_boundaries(self) -> None:
        values = self.valid_inputs("red")
        values["vine_density_per_ha"] = 8999
        self.assertIs(self.registry.assess(**values).satisfied, False)

        values = self.valid_inputs("red")
        values["irrigation_mm_per_week"] = 0.01
        self.assertIs(self.registry.assess(**values).satisfied, False)

        values = self.valid_inputs("red")
        values["parcel_crop_load_kg_ha"] = 9000.01
        self.assertIs(self.registry.assess(**values).satisfied, False)

        values = self.valid_inputs("white")
        values["parcel_crop_load_kg_ha"] = 10500.01
        self.assertIs(self.registry.assess(**values).satisfied, False)

    def test_foule_uses_strict_half_meter_operator(self) -> None:
        values = self.valid_inputs("red")
        values.update(
            planting_pattern="foule",
            row_spacing_m=None,
            support_system="stake",
            canopy_height_m=None,
            vine_spacing_m=0.50,
        )
        self.assertIs(self.registry.assess(**values).satisfied, False)
        values["vine_spacing_m"] = 0.51
        self.assertIs(self.registry.assess(**values).satisfied, True)

    def test_dead_missing_vines_feed_national_proportional_yield_remedy(self) -> None:
        at_threshold = self.yields.assess(
            country="France",
            appellation="Marsannay",
            dead_missing_vine_fraction=0.20,
        )
        above = self.yields.assess(
            country="France",
            appellation="Marsannay",
            dead_missing_vine_fraction=0.25,
        )
        self.assertEqual(at_threshold.multiplier, 1.0)
        self.assertAlmostEqual(above.multiplier, 0.75)
        self.assertIn("threshold-source:marsannay_masa_2020_cdc", above.evidence)
        self.assertIn("remedy-source:fr_code_rural_d645_4", above.evidence)


if __name__ == "__main__":
    unittest.main()
