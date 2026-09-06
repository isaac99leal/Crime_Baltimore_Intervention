from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge import VineyardBlock, VineyardEngine, WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory
from sommelier_v2.knowledge.regional_rules import OriginConstraintError
from sommelier_v2.knowledge.vineyard_legal_constraints import VineyardLegalConstraintRegistry
from sommelier_v2.knowledge.vineyard_yield_adjustments import VineyardYieldAdjustmentRegistry
from sommelier_v2.knowledge.vintage_engine import DailyWeather


PREMIER_CRUS = {
    "Aux Beaux Bruns", "Aux Combottes", "Aux Echanges", "Derrière la Grange",
    "La Combe d'Orveau", "Les Amoureuses", "Les Baudes", "Les Borniques",
    "Les Carrières", "Les Chabiots", "Les Charmes", "Les Chatelots",
    "Les Combottes", "Les Cras", "Les Feusselottes", "Les Fuées",
    "Les Groseilles", "Les Gruenchers", "Les Hauts Doix", "Les Lavrottes",
    "Les Noirots", "Les Plantes", "Les Sentiers", "Les Véroilles",
}

LIEUX_DITS = {
    "Aux Croix", "Derrière le Four", "La Combe d'Orveau", "La Taupe", "Le Village",
    "Les Argillières", "Les Athets", "Les Babillères", "Les Barottes", "Les Bas Doix",
    "Les Bussières", "Les Chardannes", "Les Clos", "Les Clos de l'Orme", "Les Condemennes",
    "Les Cras", "Les Creux Baissants", "Les Danguerrins", "Les Drazey", "Les Echezeaux",
    "Les Fouchères", "Les Fremières", "Les Gamaires", "Les Guérippes", "Les Herbues",
    "Les Jutruots", "Les Mal Carrées", "Les Maladières", "Les Mombies", "Les Nazoires",
    "Les Pas de Chat", "Les Porlottes", "Les Sordes",
}


class ChambolleSiteRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = WorldWineKnowledgeCatalog()
        cls.rows = [site for site in cls.catalog.named_sites if site.parent == "Chambolle-Musigny"]

    def test_exact_premier_cru_and_lieu_dit_sets(self) -> None:
        climats = {site.name for site in self.rows if site.site_type == "climat"}
        lieux_dits = {site.name for site in self.rows if site.site_type == "lieu_dit"}
        self.assertEqual(climats, PREMIER_CRUS)
        self.assertEqual(lieux_dits, LIEUX_DITS)
        self.assertEqual(len(climats), 24)
        self.assertEqual(len(lieux_dits), 33)

    def test_same_name_climat_and_lieu_dit_remain_distinct(self) -> None:
        for name in ("Les Cras", "La Combe d'Orveau"):
            rows = [site for site in self.rows if site.name == name]
            self.assertEqual({site.site_type for site in rows}, {"climat", "lieu_dit"})
            self.assertEqual(len({site.id for site in rows}), 2)

    def test_feusselottes_keeps_explicit_alias(self) -> None:
        site = next(
            site for site in self.rows
            if site.name == "Les Feusselottes" and site.site_type == "climat"
        )
        self.assertIn("Les Feusselotes", site.aliases)
        self.assertEqual(site.legal_status, "official_appellation_climat")


class ChambolleParentLegalSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = LegalSpecRegistry()

    def spec(self, variant: str):
        row = self.registry.resolve(
            country="France",
            appellation="Chambolle-Musigny",
            variant=variant,
        )
        self.assertIsNotNone(row)
        return row

    def test_existing_parent_specs_remain_unique_and_executable(self) -> None:
        standard = self.spec("standard")
        premier = self.spec("premier cru")
        self.assertEqual(
            (standard.min_potential_alcohol_pct, standard.max_yield_hl_ha),
            (10.5, 50.0),
        )
        self.assertEqual(
            (premier.min_potential_alcohol_pct, premier.max_yield_hl_ha),
            (11.0, 48.0),
        )
        for row in (standard, premier):
            self.assertEqual(row.max_residual_sugar_g_l, 2.0)
            self.assertEqual(row.max_malic_acid_g_l, 0.4)

    def test_ministry_source_is_available_without_duplicate_parent_spec(self) -> None:
        self.assertIn("chambolle_masa_2011_cdc", self.registry.sources)
        ids = [row.id for row in self.registry.specs]
        self.assertEqual(ids.count("fr:chambolle-musigny:standard"), 1)
        self.assertEqual(ids.count("fr:chambolle-musigny:premier-cru"), 1)

    def test_mixed_planted_accessory_grapes_do_not_become_cellar_blend_options(self) -> None:
        row = self.spec("premier cru")
        self.assertTrue(self.registry.evaluate_blend(row, "Pinot Noir").eligible)
        for accessory in ("Chardonnay", "Pinot Blanc", "Pinot Gris"):
            decision = self.registry.evaluate_blend(
                row,
                {"Pinot Noir": 95, accessory: 5},
            )
            self.assertFalse(decision.eligible)
            self.assertEqual(decision.status, "grape_not_permitted_for_appellation")

    def test_encoded_parent_yield_and_natural_alcohol_boundaries_execute(self) -> None:
        row = self.spec("premier cru")
        self.assertTrue(
            self.registry.validate_production(
                row,
                wine_yield_hl_ha=48.0,
                potential_alcohol_pct=11.0,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                row,
                wine_yield_hl_ha=48.01,
                potential_alcohol_pct=11.0,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                row,
                wine_yield_hl_ha=48.0,
                potential_alcohol_pct=10.99,
            ).eligible
        )


class ChambolleSiteClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.factory = WineOriginFactory()

    @classmethod
    def site(cls, name: str, site_type: str):
        return next(
            site for site in cls.factory.catalog.named_sites
            if site.parent == "Chambolle-Musigny"
            and site.name == name
            and site.site_type == site_type
        )

    def create(self, site, variant: str, *, claimed_site_name: str | None = None):
        return self.factory.create(
            OriginRequest(
                country="France",
                region="Bourgogne",
                appellation="Chambolle-Musigny",
                grapes={"Pinot Noir": 100},
                vintage_year=2025,
                label_scope="regulated_gi",
                site_id=site.id,
                claimed_site_name=claimed_site_name,
                wine_variant=variant,
            )
        )

    def test_premier_cru_climat_claim_passes(self) -> None:
        origin = self.create(self.site("Les Amoureuses", "climat"), "premier cru")
        self.assertTrue(origin.site_claim_eligible)
        self.assertEqual(
            origin.site_claim_rule_id,
            "siteclaim:fr:chambolle-musigny:premier-cru-climat",
        )

    def test_alternate_feusselotes_spelling_is_explicitly_authorized(self) -> None:
        site = self.site("Les Feusselottes", "climat")
        origin = self.create(
            site,
            "premier cru",
            claimed_site_name="Les Feusselotes",
        )
        self.assertTrue(origin.site_claim_eligible)
        self.assertEqual(origin.site_claim_name, "Les Feusselotes")
        self.assertIn(
            "authorized_cover_claim:Les Feusselotes",
            origin.site_claim_evidence,
        )

    def test_premier_cru_site_requires_premier_cru_production_path(self) -> None:
        origin = self.create(self.site("Les Cras", "climat"), "standard")
        self.assertFalse(origin.site_claim_eligible)
        self.assertEqual(
            origin.site_claim_status,
            "site_claim_rule_conditions_not_met",
        )

    def test_ordinary_lieu_dit_does_not_inherit_same_name_pc_authority(self) -> None:
        origin = self.create(self.site("Les Cras", "lieu_dit"), "standard")
        self.assertFalse(origin.site_claim_eligible)
        self.assertEqual(origin.site_claim_status, "site_claim_rule_unverified")

    def test_white_wine_is_not_a_positive_chambolle_origin_path(self) -> None:
        site = self.site("Les Amoureuses", "climat")
        with self.assertRaises(OriginConstraintError):
            self.factory.create(
                OriginRequest(
                    country="France",
                    region="Bourgogne",
                    appellation="Chambolle-Musigny",
                    grapes={"Chardonnay": 100},
                    vintage_year=2025,
                    label_scope="regulated_gi",
                    site_id=site.id,
                    wine_variant="premier cru",
                )
            )


class ChambolleVineyardLawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = VineyardLegalConstraintRegistry()
        cls.yields = VineyardYieldAdjustmentRegistry()

    @staticmethod
    def valid_inputs() -> dict[str, object]:
        return {
            "country": "France",
            "appellation": "Chambolle-Musigny",
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

    def test_complete_reviewed_vineyard_path_passes(self) -> None:
        assessment = self.registry.assess(**self.valid_inputs())
        self.assertIs(assessment.satisfied, True)
        self.assertIn("source:chambolle_masa_2011_cdc", assessment.evidence)

    def test_foule_half_meter_operator_is_strict(self) -> None:
        values = self.valid_inputs()
        values.update(
            planting_pattern="foule",
            row_spacing_m=None,
            support_system="stake",
            canopy_height_m=None,
        )
        values["vine_spacing_m"] = 0.50
        self.assertIs(self.registry.assess(**values).satisfied, False)
        values["vine_spacing_m"] = 0.51
        self.assertIs(self.registry.assess(**values).satisfied, True)

    def test_dead_missing_vines_use_national_proportional_remedy(self) -> None:
        threshold = self.yields.assess(
            country="France",
            appellation="Chambolle-Musigny",
            dead_missing_vine_fraction=0.20,
        )
        above = self.yields.assess(
            country="France",
            appellation="Chambolle-Musigny",
            dead_missing_vine_fraction=0.25,
        )
        self.assertEqual(threshold.multiplier, 1.0)
        self.assertAlmostEqual(above.multiplier, 0.75)
        self.assertIn(
            "threshold-source:chambolle_masa_2011_cdc",
            above.evidence,
        )
        self.assertIn("remedy-source:fr_code_rural_d645_4", above.evidence)

    @staticmethod
    def weather() -> list[DailyWeather]:
        return [
            DailyWeather(
                day_of_year=doy,
                tmin_c=16.0,
                tmax_c=31.0,
                rain_mm=0.5,
                humidity_pct=50.0,
                solar_mj_m2=22.0,
                wind_m_s=2.0,
            )
            for doy in range(80, 311)
        ]

    def test_full_legal_vineyard_engine_can_use_chambolle_site(self) -> None:
        catalog = WorldWineKnowledgeCatalog()
        site = next(
            site for site in catalog.named_sites
            if site.parent == "Chambolle-Musigny"
            and site.name == "Les Amoureuses"
            and site.site_type == "climat"
        )
        block = VineyardBlock(
            id="chambolle-amoureuses",
            grape="Pinot Noir",
            area_ha=1.0,
            planting_year=2000,
            country="France",
            region="Bourgogne",
            appellation="Chambolle-Musigny",
            site_id=site.id,
            wine_variant="premier cru",
            label_scope="regulated_gi",
            vine_density_per_ha=9000,
            irrigation_mm_per_week=0.0,
            planting_pattern="rows",
            row_spacing_m=1.25,
            vine_spacing_m=0.50,
            target_yield_t_ha=4.0,
            pruning_system="guyot_simple",
            retained_buds_per_vine=8,
            fruiting_shoots_per_vine=8,
            support_system="trellis",
            canopy_height_m=0.75,
            parcel_crop_load_kg_ha=9000.0,
            dead_missing_vine_fraction=0.20,
        )
        result = VineyardEngine().simulate(
            block,
            self.weather(),
            vintage_year=2026,
        )
        self.assertTrue(result.harvestable)
        self.assertTrue(result.label_eligible)
        self.assertTrue(result.site_claim_eligible)


class ChambolleAuthoritativeCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = AuthoritativeCatalogGenerator()
        cls.items = cls.generator.generate(as_of_year=2026, include_site_claims=True)

    def test_authoritative_generator_uses_enriched_registry_and_all_24_pc_sites(self) -> None:
        sites = {
            item.wine.vineyard
            for item in self.items
            if item.legal_spec_id == "fr:chambolle-musigny:premier-cru"
            and item.wine.vineyard
        }
        self.assertEqual(sites, PREMIER_CRUS)


if __name__ == "__main__":
    unittest.main()
