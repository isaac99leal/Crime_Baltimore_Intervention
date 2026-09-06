from __future__ import annotations

import unittest

from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory
from sommelier_v2.knowledge.site_claims import SiteClaimRegistry
from sommelier_v2.knowledge.vineyard_legal_constraints import VineyardLegalConstraintRegistry
from sommelier_v2.knowledge.vineyard_registry import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.vineyard_yield_adjustments import VineyardYieldAdjustmentRegistry


CLAIM_EVIDENCE = (
    "cadastral_lieu_dit_confirmed",
    "harvest_declaration_site_confirmed",
)


class MarsannayLegalSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()
        cls.specs = [
            spec for spec in cls.registry.specs
            if spec.country == "France" and spec.appellation == "Marsannay"
        ]

    def spec(self, variant: str):
        spec = self.registry.resolve(
            country="France", appellation="Marsannay", variant=variant
        )
        self.assertIsNotNone(spec)
        return spec

    def test_current_law_has_exactly_three_color_paths_and_no_premier_cru(self):
        self.assertEqual({spec.variant for spec in self.specs}, {"white", "red", "rose"})
        self.assertEqual(len(self.specs), 3)
        self.assertFalse(any("premier" in spec.variant.casefold() for spec in self.specs))
        self.assertFalse(any("premier-cru" in spec.id.casefold() for spec in self.specs))

    def test_exact_maturity_and_yield_matrix(self):
        white = self.spec("white")
        red = self.spec("red")
        rose = self.spec("rose")
        self.assertEqual((white.min_must_sugar_g_l, white.min_potential_alcohol_pct, white.max_yield_hl_ha), (178.0, 11.0, 57.0))
        self.assertEqual((red.min_must_sugar_g_l, red.min_potential_alcohol_pct, red.max_yield_hl_ha), (180.0, 10.5, 50.0))
        self.assertEqual((rose.min_must_sugar_g_l, rose.min_potential_alcohol_pct, rose.max_yield_hl_ha), (180.0, 10.5, 60.0))

        self.assertTrue(self.registry.validate_production(white, wine_yield_hl_ha=57.0, must_sugar_g_l=178.0, potential_alcohol_pct=11.0).eligible)
        self.assertFalse(self.registry.validate_production(white, wine_yield_hl_ha=57.01, must_sugar_g_l=178.0, potential_alcohol_pct=11.0).eligible)
        self.assertFalse(self.registry.validate_production(red, wine_yield_hl_ha=50.0, must_sugar_g_l=179.99, potential_alcohol_pct=10.5).eligible)
        self.assertTrue(self.registry.validate_production(rose, wine_yield_hl_ha=60.0, must_sugar_g_l=180.0, potential_alcohol_pct=10.5).eligible)

    def test_white_pinot_gris_cap_and_conservative_red_accessory_path(self):
        white = self.spec("white")
        red = self.spec("red")
        self.assertTrue(self.registry.evaluate_blend(white, {"Chardonnay": 70, "Pinot Gris": 30}).eligible)
        self.assertFalse(self.registry.evaluate_blend(white, {"Chardonnay": 69, "Pinot Gris": 31}).eligible)
        self.assertTrue(self.registry.evaluate_blend(white, "Pinot Blanc").eligible)
        self.assertTrue(self.registry.evaluate_blend(red, "Pinot Noir").eligible)
        self.assertFalse(self.registry.evaluate_blend(red, {"Pinot Noir": 90, "Chardonnay": 10}).eligible)

    def test_red_malic_and_color_specific_total_alcohol(self):
        white = self.spec("white")
        red = self.spec("red")
        rose = self.spec("rose")
        self.assertEqual((white.max_total_alcohol_pct, red.max_total_alcohol_pct, rose.max_total_alcohol_pct), (13.5, 13.5, 13.0))
        self.assertEqual(red.max_malic_acid_g_l, 0.4)
        self.assertFalse(self.registry.validate_release(red, total_aging_months=0, total_alcohol_pct=13.5, residual_sugar_g_l=2.0, malic_acid_g_l=0.41).eligible)
        self.assertFalse(self.registry.validate_release(rose, total_aging_months=0, total_alcohol_pct=13.01, residual_sugar_g_l=3.0).eligible)

    def test_white_and_red_exact_calendar_but_rose_calendar_is_not_invented(self):
        for variant, total_alcohol, sugar, malic in (
            ("white", 13.5, 3.0, None),
            ("red", 13.5, 2.0, 0.4),
        ):
            spec = self.spec(variant)
            self.assertEqual((spec.min_elevage_year_offset, spec.min_elevage_until_month, spec.min_elevage_until_day), (1, 6, 15))
            self.assertEqual((spec.release_year_offset, spec.earliest_release_month, spec.earliest_release_day), (1, 6, 30))
            kwargs = dict(
                total_aging_months=0,
                total_alcohol_pct=total_alcohol,
                residual_sugar_g_l=sugar,
                vintage_year=2026,
                elevage_end_year=2027,
                elevage_end_month=6,
                elevage_end_day=15,
                release_year=2027,
                release_month=6,
                release_day=30,
            )
            if malic is not None:
                kwargs["malic_acid_g_l"] = malic
            self.assertTrue(self.registry.validate_release(spec, **kwargs).eligible)
            early = dict(kwargs)
            early["release_day"] = 29
            self.assertFalse(self.registry.validate_release(spec, **early).eligible)

        rose = self.spec("rose")
        self.assertIsNone(rose.min_elevage_until_month)
        self.assertIsNone(rose.release_year_offset)
        self.assertIsNone(rose.earliest_release_month)
        self.assertIsNone(rose.earliest_release_day)


class MarsannaySiteIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = WorldWineKnowledgeCatalog()
        cls.rows = [site for site in cls.catalog.named_sites if site.parent == "Marsannay"]

    def test_source_backed_identity_counts(self):
        main = [site for site in self.rows if "bivb_marsannay" in site.source_ids]
        rose = [site for site in self.rows if "bivb_marsannay_rose" in site.source_ids]
        self.assertEqual(len(main), 78)
        self.assertEqual(len(rose), 36)
        self.assertEqual(len(self.rows), 107)
        self.assertTrue(all(site.site_type == "lieu_dit" for site in self.rows))

    def test_overlapping_identity_accumulates_both_source_views(self):
        row = next(site for site in self.rows if site.name == "Au Larrey")
        self.assertIn("bivb_marsannay", row.source_ids)
        self.assertIn("bivb_marsannay_rose", row.source_ids)

    def test_combe_vaulon_is_one_normalized_identity(self):
        rows = [site for site in self.rows if site.name == "La Combe Vaulon"]
        self.assertEqual(len(rows), 1)
        self.assertFalse(any(site.name == "La CombeVaulon" for site in self.rows))
        self.assertIn("bivb_marsannay", rows[0].source_ids)
        self.assertIn("bivb_marsannay_rose", rows[0].source_ids)

    def test_pending_premier_cru_project_is_not_current_site_classification(self):
        self.assertFalse(any(site.classification and "Premier Cru" in site.classification for site in self.rows))
        self.assertFalse(any(site.site_type == "climat" for site in self.rows))


class MarsannaySiteClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = WineOriginFactory()
        cls.claims = SiteClaimRegistry()

    @classmethod
    def site(cls, name: str):
        return next(site for site in cls.factory.catalog.named_sites if site.parent == "Marsannay" and site.name == name)

    def origin(self, site_name: str, *, variant: str, evidence=()):
        site = self.site(site_name)
        grapes = {
            "white": {"Chardonnay": 100},
            "red": {"Pinot Noir": 100},
            "rose": {"Pinot Noir": 100},
        }[variant]
        return self.factory.create(
            OriginRequest(
                country="France",
                region="Bourgogne",
                appellation="Marsannay",
                grapes=grapes,
                vintage_year=2026,
                label_scope="regulated_gi",
                site_id=site.id,
                wine_variant=variant,
                site_claim_evidence=tuple(evidence),
            )
        )

    def test_bivb_identity_alone_does_not_authorize_lieu_dit_label(self):
        origin = self.origin("Clos du Roy", variant="red")
        self.assertFalse(origin.site_claim_eligible)
        self.assertEqual(origin.site_claim_status, "site_claim_rule_conditions_not_met")

    def test_both_documentary_predicates_are_required(self):
        only_cadastral = self.origin(
            "Clos du Roy", variant="red", evidence=("cadastral_lieu_dit_confirmed",)
        )
        self.assertFalse(only_cadastral.site_claim_eligible)

        complete = self.origin("Clos du Roy", variant="red", evidence=CLAIM_EVIDENCE)
        self.assertTrue(complete.site_claim_eligible)
        self.assertEqual(complete.site_claim_rule_id, "siteclaim:fr:marsannay:white-red:cadastral-lieu-dit")
        self.assertIn("claim_evidence:cadastral_lieu_dit_confirmed", complete.site_claim_evidence)
        self.assertIn("claim_evidence:harvest_declaration_site_confirmed", complete.site_claim_evidence)

    def test_rose_only_identity_requires_rose_rule_and_same_documentary_evidence(self):
        self.assertTrue(self.origin("Aux Avoines", variant="rose", evidence=CLAIM_EVIDENCE).site_claim_eligible)
        red = self.origin("Aux Avoines", variant="red", evidence=CLAIM_EVIDENCE)
        self.assertFalse(red.site_claim_eligible)
        self.assertEqual(red.site_claim_status, "site_claim_rule_conditions_not_met")

    def test_claim_evidence_is_lot_specific_not_site_metadata(self):
        site = self.site("Clos du Roy")
        self.assertNotIn("cadastral_lieu_dit_confirmed", site.source_ids)
        self.assertNotIn("harvest_declaration_site_confirmed", site.source_ids)


class MarsannayVineyardLawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.constraints = VineyardLegalConstraintRegistry()
        cls.adjustments = VineyardYieldAdjustmentRegistry()

    @staticmethod
    def complete_state(*, style: str, crop_load: float, buds: int):
        return dict(
            country="France",
            appellation="Marsannay",
            vine_density_per_ha=9000,
            irrigation_mm_per_week=0.0,
            planting_pattern="rows",
            row_spacing_m=1.25,
            vine_spacing_m=0.50,
            wine_style=style,
            pruning_system="cordon_royat",
            retained_buds_per_vine=buds,
            fruiting_shoots_per_vine=buds,
            support_system="trellis",
            canopy_height_m=0.75,
            parcel_crop_load_kg_ha=crop_load,
        )

    def test_red_and_white_reviewed_management_boundaries(self):
        red = self.constraints.assess(**self.complete_state(style="red", crop_load=9000, buds=8))
        white = self.constraints.assess(**self.complete_state(style="white", crop_load=10500, buds=10))
        self.assertTrue(red.satisfied)
        self.assertTrue(white.satisfied)

        red_high = self.constraints.assess(**self.complete_state(style="red", crop_load=9000.1, buds=8))
        white_high_buds = self.constraints.assess(**self.complete_state(style="white", crop_load=10500, buds=11))
        self.assertFalse(red_high.satisfied)
        self.assertFalse(white_high_buds.satisfied)

    def test_geometry_irrigation_and_foule_operators(self):
        wet = self.constraints.assess(**{**self.complete_state(style="red", crop_load=9000, buds=8), "irrigation_mm_per_week": 0.01})
        self.assertFalse(wet.satisfied)
        foule_half = self.constraints.assess(**{**self.complete_state(style="red", crop_load=9000, buds=8), "planting_pattern": "foule", "row_spacing_m": None, "vine_spacing_m": 0.50, "support_system": "stake", "canopy_height_m": None})
        foule_good = self.constraints.assess(**{**self.complete_state(style="red", crop_load=9000, buds=8), "planting_pattern": "foule", "row_spacing_m": None, "vine_spacing_m": 0.51, "support_system": "stake", "canopy_height_m": None})
        self.assertFalse(foule_half.satisfied)
        self.assertTrue(foule_good.satisfied)

    def test_rose_management_is_not_silently_borrowed_from_red(self):
        rose = self.constraints.assess(**self.complete_state(style="rose", crop_load=10500, buds=8))
        self.assertIsNone(rose.satisfied)
        self.assertEqual(rose.status, "vineyard_law_evidence_incomplete")

    def test_chablis_pruning_is_not_generalized_to_all_white_grapes(self):
        state = self.complete_state(style="white", crop_load=10500, buds=8)
        state["pruning_system"] = "chablis"
        assessment = self.constraints.assess(**state)
        self.assertIsNone(assessment.satisfied)

    def test_dead_missing_vines_use_existing_national_proportional_remedy(self):
        at_threshold = self.adjustments.assess(
            country="France", appellation="Marsannay", dead_missing_vine_fraction=0.20
        )
        over = self.adjustments.assess(
            country="France", appellation="Marsannay", dead_missing_vine_fraction=0.25
        )
        self.assertEqual(at_threshold.multiplier, 1.0)
        self.assertEqual(over.multiplier, 0.75)
        self.assertIn("remedy-source:fr_code_rural_d645_4", over.evidence)
        self.assertIn("threshold-source:marsannay_masa_2020_current", over.evidence)


if __name__ == "__main__":
    unittest.main()
