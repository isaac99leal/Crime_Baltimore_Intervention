from __future__ import annotations

import unittest

from sommelier_v2.knowledge.regional_rules import OriginDecision
from sommelier_v2.knowledge.site_claims import SiteClaimRegistry
from sommelier_v2.knowledge.vineyard_registry import WorldWineKnowledgeCatalog


class PiedmontMga2026Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = WorldWineKnowledgeCatalog()
        cls.claims = SiteClaimRegistry()
        cls.origin = OriginDecision(
            eligible=True,
            status="appellation_eligible_sourced_spec",
            label_scope="regulated_gi",
            canonical_grapes=("Nebbiolo",),
        )

    def current_sites(self, parent: str, source_id: str):
        return [
            site
            for site in self.catalog.sites(country="Italy", parent=parent, site_type="MGA")
            if source_id in site.source_ids
        ]

    def site(self, parent: str, name: str):
        matches = [
            site
            for site in self.catalog.sites(country="Italy", parent=parent, site_type="MGA")
            if site.name == name
        ]
        self.assertEqual(len(matches), 1, (parent, name, matches))
        return matches[0]

    def test_current_masaf_identity_counts_are_exact(self) -> None:
        self.assertEqual(len(self.current_sites("Barolo DOCG", "barolo_masaf_2026_mga")), 180)
        self.assertEqual(len(self.current_sites("Barbaresco DOCG", "barbaresco_masaf_2026_mga")), 66)

    def test_barolo_current_list_adds_municipality_mentions_and_briccolina(self) -> None:
        names = {
            site.name
            for site in self.current_sites("Barolo DOCG", "barolo_masaf_2026_mga")
        }
        self.assertIn("Briccolina", names)
        self.assertIn("del comune di Barolo", names)
        self.assertIn("del comune di Castiglione Falletto", names)
        self.assertIn("del comune di Serralunga d’Alba", names)
        self.assertIn("del comune di Verduno", names)
        self.assertEqual(sum(name.startswith("del comune di ") for name in names), 11)

    def test_current_barolo_corrects_legacy_spelling_and_split_parse(self) -> None:
        current_names = {
            site.name
            for site in self.current_sites("Barolo DOCG", "barolo_masaf_2026_mga")
        }
        self.assertIn("Bergeisa", current_names)
        self.assertIn("Gallaretto Garretti", current_names)
        self.assertNotIn("Bergesia", current_names)
        self.assertNotIn("Gallaretto", current_names)
        self.assertNotIn("Garretti", current_names)

        # The old seed rows can remain as provenance/history, but 2026 authority
        # is deliberately not attached to them, so they cannot support a current MGA claim.
        for stale_name in ("Bergesia", "Gallaretto", "Garretti"):
            stale = self.site("Barolo DOCG", stale_name)
            self.assertNotIn("barolo_masaf_2026_mga", stale.source_ids)
            decision = self.claims.evaluate(
                site=stale,
                origin_decision=self.origin,
                appellation="Barolo DOCG",
            )
            self.assertFalse(decision.eligible)

    def test_current_barolo_mga_claims_require_masaf_identity_evidence(self) -> None:
        current = self.site("Barolo DOCG", "Bergeisa")
        decision = self.claims.evaluate(
            site=current,
            origin_decision=self.origin,
            appellation="Barolo DOCG",
        )
        self.assertTrue(decision.eligible)
        self.assertEqual(decision.rule_id, "siteclaim:it:barolo:mga")

    def test_barolo_article_8_alternate_names_are_explicit_cover_claims(self) -> None:
        altenasso = self.site("Barolo DOCG", "Altenasso")
        for claim in ("Garblet Suè", "Garbelletto Superiore"):
            decision = self.claims.evaluate(
                site=altenasso,
                origin_decision=self.origin,
                appellation="Barolo DOCG",
                claimed_site_name=claim,
            )
            self.assertTrue(decision.eligible, (claim, decision))
            self.assertEqual(decision.claim_name, claim)

        cannubi_boschis = self.site("Barolo DOCG", "Cannubi Boschis")
        decision = self.claims.evaluate(
            site=cannubi_boschis,
            origin_decision=self.origin,
            appellation="Barolo DOCG",
            claimed_site_name="Cannubi",
        )
        self.assertTrue(decision.eligible)
        self.assertEqual(decision.claim_name, "Cannubi")

        mariondino = self.site("Barolo DOCG", "Mariondino")
        for claim in ("Monriondino", "Bricco Moriondino"):
            self.assertTrue(
                self.claims.evaluate(
                    site=mariondino,
                    origin_decision=self.origin,
                    appellation="Barolo DOCG",
                    claimed_site_name=claim,
                ).eligible
            )

    def test_barbaresco_current_mga_claim_is_source_gated(self) -> None:
        asili = self.site("Barbaresco DOCG", "Asili")
        self.assertIn("barbaresco_masaf_2026_mga", asili.source_ids)
        decision = self.claims.evaluate(
            site=asili,
            origin_decision=self.origin,
            appellation="Barbaresco DOCG",
        )
        self.assertTrue(decision.eligible)
        self.assertEqual(decision.rule_id, "siteclaim:it:barbaresco:mga")

    def test_vigna_toponym_is_not_promoted_to_mga_authority(self) -> None:
        barolo_rule = next(rule for rule in self.claims.rules if rule.id == "siteclaim:it:barolo:mga")
        barbaresco_rule = next(rule for rule in self.claims.rules if rule.id == "siteclaim:it:barbaresco:mga")
        self.assertEqual(barolo_rule.site_type, "MGA")
        self.assertEqual(barbaresco_rule.site_type, "MGA")
        self.assertFalse(any(rule.site_type == "vigna" for rule in self.claims.rules if rule.country == "Italy"))


if __name__ == "__main__":
    unittest.main()
