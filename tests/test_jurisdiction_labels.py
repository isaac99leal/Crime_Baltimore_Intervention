from __future__ import annotations

import unittest

from sommelier_v2.knowledge.jurisdiction_labels import (
    BlendComponent,
    JurisdictionLabelValidator,
    LabelClaims,
)


def c(pct, grape, country, origins=(), vintage=None):
    return BlendComponent(float(pct), grape, country, tuple(origins), vintage)


class UnitedStatesLabelRulesTests(unittest.TestCase):
    def setUp(self):
        self.validator = JurisdictionLabelValidator()

    def test_napa_ava_requires_85_percent_origin_and_finishing(self):
        components = [
            c(85, "Cabernet Sauvignon", "United States", ("Napa Valley", "California"), 2025),
            c(15, "Cabernet Sauvignon", "United States", ("California",), 2025),
        ]
        claims = LabelClaims(
            jurisdiction="US", origin_names=("Napa Valley",), origin_type="AVA",
            variety_names=("Cabernet Sauvignon",), fully_finished_in_required_area=True,
        )
        self.assertTrue(self.validator.validate(components, claims).eligible)

        bad = [
            c(84, "Cabernet Sauvignon", "United States", ("Napa Valley", "California"), 2025),
            c(16, "Cabernet Sauvignon", "United States", ("California",), 2025),
        ]
        self.assertFalse(self.validator.validate(bad, claims).eligible)

    def test_us_varietal_share_must_also_come_from_labeled_appellation(self):
        components = [
            c(70, "Cabernet Sauvignon", "United States", ("Napa Valley", "California"), 2025),
            c(10, "Cabernet Sauvignon", "United States", ("Sonoma Valley", "California"), 2025),
            c(20, "Merlot", "United States", ("Napa Valley", "California"), 2025),
        ]
        claims = LabelClaims(
            jurisdiction="US", origin_names=("Napa Valley",), origin_type="AVA",
            variety_names=("Cabernet Sauvignon",), fully_finished_in_required_area=True,
        )
        decision = self.validator.validate(components, claims)
        self.assertFalse(decision.eligible)
        self.assertTrue(any("both Cabernet Sauvignon" in issue for issue in decision.issues))

    def test_us_multi_variety_requires_every_grape_and_percentages(self):
        components = [
            c(60, "Cabernet Sauvignon", "United States", ("California",), 2025),
            c(40, "Merlot", "United States", ("California",), 2025),
        ]
        claims = LabelClaims(
            jurisdiction="US", origin_names=("California",), origin_type="state",
            variety_names=("Cabernet Sauvignon", "Merlot"),
            shown_variety_percentages=True, fully_finished_in_required_area=True,
        )
        self.assertTrue(self.validator.validate(components, claims).eligible)
        no_pct = LabelClaims(
            jurisdiction="US", origin_names=("California",), origin_type="state",
            variety_names=("Cabernet Sauvignon", "Merlot"),
            shown_variety_percentages=False, fully_finished_in_required_area=True,
        )
        self.assertFalse(self.validator.validate(components, no_pct).eligible)

    def test_us_ava_vintage_requires_95_percent(self):
        components = [
            c(94, "Cabernet Sauvignon", "United States", ("Napa Valley", "California"), 2025),
            c(6, "Cabernet Sauvignon", "United States", ("Napa Valley", "California"), 2024),
        ]
        claims = LabelClaims(
            jurisdiction="US", origin_names=("Napa Valley",), origin_type="AVA",
            vintage_years=(2025,), fully_finished_in_required_area=True,
        )
        self.assertFalse(self.validator.validate(components, claims).eligible)
        passing = [
            c(95, "Cabernet Sauvignon", "United States", ("Napa Valley", "California"), 2025),
            c(5, "Cabernet Sauvignon", "United States", ("Napa Valley", "California"), 2024),
        ]
        self.assertTrue(self.validator.validate(passing, claims).eligible)


class AustraliaLabelRulesTests(unittest.TestCase):
    def setUp(self):
        self.validator = JurisdictionLabelValidator()

    def test_barossa_single_gi_and_variety_use_85_percent_rule(self):
        components = [
            c(85, "Shiraz", "Australia", ("Barossa Valley", "South Australia"), 2025),
            c(15, "Grenache", "Australia", ("McLaren Vale", "South Australia"), 2025),
        ]
        claims = LabelClaims(
            jurisdiction="Australia", origin_names=("Barossa Valley",),
            variety_names=("Shiraz",), vintage_years=(2025,),
        )
        self.assertTrue(self.validator.validate(components, claims).eligible)

    def test_multiple_australian_origins_need_95_total_5_each_and_descending(self):
        components = [
            c(60, "Shiraz", "Australia", ("Barossa Valley",), 2025),
            c(30, "Shiraz", "Australia", ("McLaren Vale",), 2025),
            c(5, "Shiraz", "Australia", ("Clare Valley",), 2025),
            c(5, "Shiraz", "Australia", ("Yarra Valley",), 2025),
        ]
        claims = LabelClaims(
            jurisdiction="Australia",
            origin_names=("Barossa Valley", "McLaren Vale", "Clare Valley"),
        )
        self.assertTrue(self.validator.validate(components, claims).eligible)

        only_ninety = LabelClaims(
            jurisdiction="Australia", origin_names=("Barossa Valley", "McLaren Vale")
        )
        self.assertFalse(self.validator.validate(components, only_ninety).eligible)

    def test_australian_multi_variety_ordering_and_named_total(self):
        components = [
            c(60, "Shiraz", "Australia", ("South Australia",), 2025),
            c(25, "Grenache", "Australia", ("South Australia",), 2025),
            c(15, "Mourvedre", "Australia", ("South Australia",), 2025),
        ]
        claims = LabelClaims(
            jurisdiction="Australia", variety_names=("Shiraz", "Grenache")
        )
        self.assertTrue(self.validator.validate(components, claims).eligible)
        reversed_claim = LabelClaims(
            jurisdiction="Australia", variety_names=("Grenache", "Shiraz")
        )
        self.assertFalse(self.validator.validate(components, reversed_claim).eligible)


class NewZealandLabelRulesTests(unittest.TestCase):
    def setUp(self):
        self.validator = JurisdictionLabelValidator()

    def test_registered_marlborough_gi_requires_85_percent_and_nz_remainder(self):
        components = [
            c(85, "Sauvignon Blanc", "New Zealand", ("Marlborough",), 2025),
            c(15, "Sauvignon Blanc", "New Zealand", ("Nelson",), 2025),
        ]
        claims = LabelClaims(
            jurisdiction="New Zealand", origin_names=("Marlborough",),
            registered_nz_gi=True,
        )
        self.assertTrue(self.validator.validate(components, claims).eligible)

        foreign_remainder = [
            c(85, "Sauvignon Blanc", "New Zealand", ("Marlborough",), 2025),
            c(15, "Sauvignon Blanc", "Australia", ("Tasmania",), 2025),
        ]
        self.assertFalse(self.validator.validate(foreign_remainder, claims).eligible)

    def test_nz_combination_claim_requires_85_percent_intersection(self):
        passing = [
            c(85, "Pinot Noir", "New Zealand", ("Marlborough",), 2025),
            c(15, "Chardonnay", "New Zealand", ("Nelson",), 2024),
        ]
        claims = LabelClaims(
            jurisdiction="NZ", origin_names=("Marlborough",),
            variety_names=("Pinot Noir",), vintage_years=(2025,),
            registered_nz_gi=True,
        )
        self.assertTrue(self.validator.validate(passing, claims).eligible)

        failing = [
            c(84, "Pinot Noir", "New Zealand", ("Marlborough",), 2025),
            c(16, "Chardonnay", "New Zealand", ("Nelson",), 2024),
        ]
        self.assertFalse(self.validator.validate(failing, claims).eligible)


if __name__ == "__main__":
    unittest.main()
