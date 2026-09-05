from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


GRAND_CRUS = {
    "Echezeaux": "fr:echezeaux:grand-cru",
    "Grands-Echezeaux": "fr:grands-echezeaux:grand-cru",
    "Romanée-Saint-Vivant": "fr:romanee-saint-vivant:grand-cru",
    "Romanée-Conti": "fr:romanee-conti:grand-cru",
    "La Romanée": "fr:la-romanee:grand-cru",
    "La Tâche": "fr:la-tache:grand-cru",
    "Richebourg": "fr:richebourg:grand-cru",
    "La Grande Rue": "fr:la-grande-rue:grand-cru",
}


class VosneGrandCruLegalSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_all_eight_grand_cru_aocs_are_loaded(self):
        resolved = {
            name: self.registry.resolve(
                country="France", appellation=name, variant="grand cru"
            )
            for name in GRAND_CRUS
        }
        self.assertTrue(all(resolved.values()))
        self.assertEqual({spec.id for spec in resolved.values() if spec}, set(GRAND_CRUS.values()))

    def test_common_machine_limits_are_exact(self):
        for name, spec_id in GRAND_CRUS.items():
            spec = self.registry.resolve(
                country="France", appellation=name, variant="grand cru"
            )
            self.assertIsNotNone(spec, name)
            self.assertEqual(spec.id, spec_id)
            self.assertEqual(spec.wine_style, "red")
            self.assertEqual(spec.min_potential_alcohol_pct, 11.5)
            self.assertEqual(spec.max_yield_hl_ha, 42.0)
            self.assertEqual(spec.max_residual_sugar_g_l, 2.0)
            self.assertEqual(spec.max_malic_acid_g_l, 0.4)
            self.assertEqual(spec.release_year_offset, 1)
            self.assertEqual(spec.allowed_grapes, ("Pinot Noir",))

    def test_grand_cru_positive_path_is_pinot_noir_only(self):
        for name in GRAND_CRUS:
            spec = self.registry.resolve(
                country="France", appellation=name, variant="grand cru"
            )
            self.assertIsNotNone(spec, name)
            self.assertTrue(self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible)
            self.assertFalse(self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible)

    def test_yield_and_analytical_limits_are_executable(self):
        spec = self.registry.resolve(
            country="France", appellation="Romanée-Conti", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        self.assertTrue(
            self.registry.validate_production(
                spec, wine_yield_hl_ha=42.0, potential_alcohol_pct=11.5
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_production(
                spec, wine_yield_hl_ha=42.01, potential_alcohol_pct=11.5
            ).eligible
        )
        self.assertTrue(
            self.registry.validate_release(
                spec,
                total_aging_months=0,
                residual_sugar_g_l=2.0,
                malic_acid_g_l=0.4,
                vintage_year=2025,
                release_year=2026,
            ).eligible
        )
        self.assertFalse(
            self.registry.validate_release(
                spec,
                total_aging_months=0,
                residual_sugar_g_l=2.01,
                malic_acid_g_l=0.4,
                vintage_year=2025,
                release_year=2026,
            ).eligible
        )

    def test_accented_echezeaux_alias_resolves(self):
        spec = self.registry.resolve(
            country="France", appellation="Échezeaux", variant="grand cru"
        )
        self.assertIsNotNone(spec)
        self.assertEqual(spec.id, "fr:echezeaux:grand-cru")


class VosneGrandCruAuthoritativeCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = AuthoritativeCatalogGenerator().generate(
            as_of_year=2026, include_site_claims=True
        )

    def test_catalog_has_one_base_record_for_each_grand_cru_spec(self):
        for appellation, spec_id in GRAND_CRUS.items():
            rows = [item for item in self.items if item.legal_spec_id == spec_id]
            self.assertEqual(len(rows), 1, (appellation, len(rows)))
            self.assertEqual(rows[0].wine.appellation, appellation)
            self.assertEqual(rows[0].wine.classification, "grand cru")
            self.assertEqual(rows[0].wine.grapes, ("Pinot Noir",))
            self.assertIsNone(rows[0].wine.vineyard)

    def test_grand_cru_aocs_are_not_generated_as_vosne_site_suffixes(self):
        prohibited = set(GRAND_CRUS)
        leaked = [
            item.wine.vineyard
            for item in self.items
            if item.wine.appellation == "Vosne-Romanée"
            and item.wine.vineyard in prohibited
        ]
        self.assertFalse(leaked)


if __name__ == "__main__":
    unittest.main()
