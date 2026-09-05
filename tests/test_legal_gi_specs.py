from __future__ import annotations

import unittest

from sommelier_v2.knowledge.legal_rules import LegalAwareRegionGrapeRulebook
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.origin_factory import OriginRequest, WineOriginFactory
from sommelier_v2.knowledge.regional_rules import OriginConstraintError


class LegalSpecRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = LegalSpecRegistry()

    def spec(self, country: str, appellation: str, variant: str | None = None):
        spec = self.registry.resolve(country=country, appellation=appellation, variant=variant)
        self.assertIsNotNone(spec)
        return spec

    def test_seed_has_multiple_strict_real_appellations(self):
        stats = self.registry.stats()
        self.assertGreaterEqual(stats["sourced_legal_wine_specs"], 16)
        self.assertGreaterEqual(stats["sourced_appellations_with_strict_specs"], 7)
        self.assertGreaterEqual(stats["legal_specs_with_blend_percentages"], 10)

    def test_brunello_is_sangiovese_only(self):
        spec = self.spec("Italy", "Brunello di Montalcino DOCG")
        self.assertTrue(self.registry.evaluate_blend(spec, {"Sangiovese": 100}).eligible)
        bad = self.registry.evaluate_blend(spec, {"Sangiovese": 90, "Merlot": 10})
        self.assertFalse(bad.eligible)
        self.assertEqual(bad.status, "grape_not_permitted_for_appellation")
        self.assertEqual(spec.max_yield_t_ha, 8.0)

    def test_barolo_and_barbaresco_are_nebbiolo_only(self):
        for appellation in ("Barolo DOCG", "Barbaresco DOCG"):
            spec = self.spec("Italy", appellation)
            self.assertTrue(self.registry.evaluate_blend(spec, "Nebbiolo").eligible)
            self.assertFalse(self.registry.evaluate_blend(spec, {"Nebbiolo": 99, "Barbera": 1}).eligible)

    def test_chianti_seed_overblocks_unenumerated_secondary_grapes(self):
        spec = self.spec("Italy", "Chianti Classico DOCG")
        self.assertTrue(self.registry.evaluate_blend(spec, {"Sangiovese": 100}).eligible)
        decision = self.registry.evaluate_blend(spec, {"Sangiovese": 80, "Cabernet Sauvignon": 20})
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.status, "grape_not_permitted_for_appellation")

    def test_rioja_has_14_authorized_varieties(self):
        spec = self.spec("Spain", "Rioja DOCa")
        self.assertEqual(len(spec.allowed_grapes), 14)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Tempranillo": 70, "Graciano": 30}).eligible)
        self.assertTrue(self.registry.evaluate_blend(spec, "Verdejo").eligible)
        self.assertFalse(self.registry.evaluate_blend(spec, "Pinot Noir").eligible)

    def test_champagne_keeps_voltis_out_of_normal_blend(self):
        spec = self.spec("France", "Champagne AOP")
        self.assertIn("Voltis", spec.vineyard_adaptation_grapes)
        self.assertEqual(spec.vineyard_adaptation_max_pct, 5.0)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Chardonnay": 60, "Pinot Noir": 40}).eligible)
        self.assertFalse(self.registry.evaluate_blend(spec, {"Chardonnay": 95, "Voltis": 5}).eligible)

    def test_prosecco_rose_enforces_both_percentage_bands(self):
        spec = self.spec("Italy", "Prosecco DOC", "rose")
        self.assertTrue(self.registry.evaluate_blend(spec, {"Glera": 85, "Pinot Nero": 15}).eligible)
        self.assertTrue(self.registry.evaluate_blend(spec, {"Glera": 90, "Pinot Nero": 10}).eligible)
        self.assertFalse(self.registry.evaluate_blend(spec, {"Glera": 95, "Pinot Nero": 5}).eligible)

    def test_release_rules_are_machine_checkable(self):
        brunello = self.spec("Italy", "Brunello di Montalcino DOCG")
        self.assertFalse(self.registry.validate_release(
            brunello, total_aging_months=48, wood_aging_months=18, bottle_aging_months=3,
            final_alcohol_pct=12.0, total_acidity_g_l=4.8, dry_extract_g_l=25.0,
        ).eligible)
        self.assertTrue(self.registry.validate_release(
            brunello, total_aging_months=60, wood_aging_months=24, bottle_aging_months=4,
            final_alcohol_pct=13.0, total_acidity_g_l=5.5, dry_extract_g_l=28.0,
        ).eligible)
        champagne = self.spec("France", "Champagne AOP", "vintage")
        self.assertFalse(self.registry.validate_release(
            champagne, total_aging_months=30, method="traditional method"
        ).eligible)
        self.assertTrue(self.registry.validate_release(
            champagne, total_aging_months=36, method="traditional method"
        ).eligible)


class LegalAwareOriginFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rulebook = LegalAwareRegionGrapeRulebook()
        cls.factory = WineOriginFactory(catalog=cls.rulebook.catalog, rulebook=cls.rulebook)

    def test_real_sourced_spec_bypasses_empty_legacy_allowed_grapes_safely(self):
        origin = self.factory.create(OriginRequest(
            country="Italy", region="Tuscany", appellation="Brunello di Montalcino DOCG",
            grapes={"Sangiovese": 100}, vintage_year=2026, label_scope="regulated_gi",
        ))
        self.assertTrue(origin.decision.eligible)
        self.assertEqual(origin.decision.status, "appellation_eligible_sourced_spec")
        self.assertTrue(origin.decision.rule_id.startswith("it:brunello"))

    def test_real_sourced_spec_blocks_impossible_grape(self):
        with self.assertRaises(OriginConstraintError):
            self.factory.create(OriginRequest(
                country="Italy", region="Piedmont", appellation="Barolo DOCG",
                grapes={"Sangiovese": 100}, vintage_year=2026, label_scope="regulated_gi",
            ))


if __name__ == "__main__":
    unittest.main()
