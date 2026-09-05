from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sommelier_v2.knowledge.expanded_catalog import NamedSite
from sommelier_v2.knowledge.regional_rules import OriginDecision
from sommelier_v2.knowledge.site_claims import SiteClaimRegistry


class SiteClaimNameFilterUnitTests(unittest.TestCase):
    def registry(self, rule: dict) -> SiteClaimRegistry:
        payload = {
            "schema_version": "1.0",
            "sources": {"legal": {"url": "https://example.invalid/legal"}},
            "rules": [rule],
        }
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        try:
            json.dump(payload, tmp)
            tmp.close()
            return SiteClaimRegistry(Path(tmp.name))
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    @staticmethod
    def origin() -> OriginDecision:
        return OriginDecision(
            eligible=True,
            status="appellation_eligible_sourced_spec",
            label_scope="regulated_gi",
            canonical_grapes=("Pinot Noir",),
            rule_id="fr:example:premier-cru",
        )

    @staticmethod
    def site(name: str) -> NamedSite:
        return NamedSite(
            id=f"site:example:{name}",
            name=name,
            country="France",
            region="Bourgogne",
            parent="Example",
            site_type="climat",
            legal_status="official_appellation_climat",
            source_ids=("identity",),
        )

    def base_rule(self) -> dict:
        return {
            "id": "siteclaim:test",
            "country": "France",
            "parent_appellation": "Example",
            "site_type": "climat",
            "required_site_legal_status": "official_appellation_climat",
            "required_site_source_ids": ["identity"],
            "allowed_wine_variants": ["premier cru"],
            "source_ids": ["legal"],
            "claim_kind": "premier_cru_climat_name",
        }

    def test_allowed_site_names_are_fail_closed(self):
        rule = self.base_rule()
        rule["allowed_site_names"] = ["Allowed"]
        registry = self.registry(rule)
        good = registry.evaluate(site=self.site("Allowed"), origin_decision=self.origin(), appellation="Example", wine_variant="premier cru")
        bad = registry.evaluate(site=self.site("Other"), origin_decision=self.origin(), appellation="Example", wine_variant="premier cru")
        self.assertTrue(good.eligible)
        self.assertFalse(bad.eligible)
        self.assertEqual(bad.status, "site_claim_rule_conditions_not_met")

    def test_excluded_site_names_override_broad_rule(self):
        rule = self.base_rule()
        rule["excluded_site_names"] = ["Blocked"]
        registry = self.registry(rule)
        good = registry.evaluate(site=self.site("Allowed"), origin_decision=self.origin(), appellation="Example", wine_variant="premier cru")
        bad = registry.evaluate(site=self.site("Blocked"), origin_decision=self.origin(), appellation="Example", wine_variant="premier cru")
        self.assertTrue(good.eligible)
        self.assertFalse(bad.eligible)

    def test_overlap_is_rejected_at_load_time(self):
        rule = self.base_rule()
        rule["allowed_site_names"] = ["Same"]
        rule["excluded_site_names"] = ["same"]
        with self.assertRaises(ValueError):
            self.registry(rule)


if __name__ == "__main__":
    unittest.main()
