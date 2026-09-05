from __future__ import annotations

import unittest

from sommelier_v2.authoritative_catalog import AuthoritativeCatalogGenerator
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry


GRAND_CRUS = {
    "Chambertin": ("fr:chambertin:grand-cru", 42.0),
    "Chambertin-Clos de Bèze": ("fr:chambertin-clos-de-beze:grand-cru", 42.0),
    "Chapelle-Chambertin": ("fr:chapelle-chambertin:grand-cru", 45.0),
    "Charmes-Chambertin": ("fr:charmes-chambertin:grand-cru", 45.0),
    "Griotte-Chambertin": ("fr:griotte-chambertin:grand-cru", 45.0),
    "Latricières-Chambertin": ("fr:latricieres-chambertin:grand-cru", 45.0),
    "Mazis-Chambertin": ("fr:mazis-chambertin:grand-cru", 45.0),
    "Mazoyères-Chambertin": ("fr:mazoyeres-chambertin:grand-cru", 45.0),
    "Ruchottes-Chambertin": ("fr:ruchottes-chambertin:grand-cru", 45.0),
}


class GevreyGrandCruLegalSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = LegalSpecRegistry()

    def test_all_nine_grand_cru_aocs_are_loaded(self):
        specs = {
            name: self.registry.resolve(
                country="France", appellation=name, variant="grand cru"
            )
            for name in GRAND_CRUS
        }
        self.assertTrue(all(specs.values()))
        self.assertEqual(
            {spec.id for spec in specs.values() if spec},
            {spec_id for spec_id, _ in GRAND_CRUS.values()},
        )

    def test_effective_yield_split_is_preserved(self):
        for name, (spec_id, expected_yield) in GRAND_CRUS.items():
            spec = self.registry.resolve(
                country="France", appellation=name, variant="grand cru"
            )
            self.assertIsNotNone(spec, name)
            self.assertEqual(spec.id, spec_id)
            self.assertEqual(spec.max_yield_hl_ha, expected_yield, name)
            self.assertEqual(spec.min_potential_alcohol_pct, 11.5, name)
            self.assertEqual(spec.max_residual_sugar_g_l, 2.0, name)
            self.assertEqual(spec.max_malic_acid_g_l, 0.4, name)
            self.assertEqual(spec.release_year_offset, 1, name)

    def test_conservative_positive_path_is_pinot_noir_only(self):
        for name in GRAND_CRUS:
            spec = self.registry.resolve(
                country="France", appellation=name, variant="grand cru"
            )
            self.assertIsNotNone(spec, name)
            self.assertTrue(
                self.registry.evaluate_blend(spec, {"Pinot Noir": 100}).eligible,
                name,
            )
            self.assertFalse(
                self.registry.evaluate_blend(spec, {"Chardonnay": 100}).eligible,
                name,
            )

    def test_yield_split_is_machine_enforced(self):
        chambertin = self.registry.resolve(
            country="France", appellation="Chambertin", variant="grand cru"
        )
        chapelle = self.registry.resolve(
            country="France", appellation="Chapelle-Chambertin", variant="grand cru"
        )
        self.assertIsNotNone(chambertin)
        self.assertIsNotNone(chapelle)
        self.assertFalse(
            self.registry.validate_production(
                chambertin, wine_yield_hl_ha=42.01, potential_alcohol_pct=11.5
            ).eligible
        )
        self.assertTrue(
            self.registry.validate_production(
                chapelle, wine_yield_hl_ha=45.0, potential_alcohol_pct=11.5
            ).eligible
        )

    def test_unaccented_aliases_resolve_without_collapsing_aocs(self):
        clos_de_beze = self.registry.resolve(
            country="France", appellation="Chambertin Clos de Beze", variant="grand cru"
        )
        latricieres = self.registry.resolve(
            country="France", appellation="Latricieres-Chambertin", variant="grand cru"
        )
        mazoyeres = self.registry.resolve(
            country="France", appellation="Mazoyeres-Chambertin", variant="grand cru"
        )
        self.assertEqual(clos_de_beze.id, "fr:chambertin-clos-de-beze:grand-cru")
        self.assertEqual(latricieres.id, "fr:latricieres-chambertin:grand-cru")
        self.assertEqual(mazoyeres.id, "fr:mazoyeres-chambertin:grand-cru")


class GevreyGrandCruCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = AuthoritativeCatalogGenerator().generate(
            as_of_year=2026, include_site_claims=True
        )

    def test_catalog_has_one_base_record_per_grand_cru_aoc(self):
        for appellation, (spec_id, _) in GRAND_CRUS.items():
            rows = [item for item in self.items if item.legal_spec_id == spec_id]
            self.assertEqual(len(rows), 1, (appellation, len(rows)))
            self.assertEqual(rows[0].wine.appellation, appellation)
            self.assertEqual(rows[0].wine.classification, "grand cru")
            self.assertEqual(rows[0].wine.grapes, ("Pinot Noir",))
            self.assertEqual(rows[0].wine.vineyard, "")

    def test_grand_cru_aocs_do_not_leak_as_gevrey_site_claims(self):
        prohibited = set(GRAND_CRUS)
        leaked = [
            item.wine.vineyard
            for item in self.items
            if item.wine.appellation == "Gevrey-Chambertin"
            and item.wine.vineyard in prohibited
        ]
        self.assertFalse(leaked)


if __name__ == "__main__":
    unittest.main()
