"""Legal-spec-aware origin rulebook.

This adapter keeps the broad legacy geographic/plausibility rulebook intact while
making sourced legal specifications the first authority for ``regulated_gi``.
If no sourced specification exists, the original fail-closed behavior remains.
"""
from __future__ import annotations

from typing import Mapping, Sequence

from .legal_specs import LegalSpecRegistry, LegalWineSpec
from .regional_rules import OriginDecision, RegionGrapeRulebook


class LegalAwareRegionGrapeRulebook(RegionGrapeRulebook):
    def __init__(self, *args, legal_specs: LegalSpecRegistry | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.legal_specs = legal_specs or LegalSpecRegistry()

    def resolve_legal_spec(
        self,
        *,
        country: str,
        appellation: str | None = None,
        region: str | None = None,
        sub_region: str | None = None,
        commune: str | None = None,
        wine_variant: str | None = None,
    ) -> LegalWineSpec | None:
        return self.legal_specs.resolve(
            country=country,
            appellation=appellation,
            region=region,
            sub_region=sub_region,
            commune=commune,
            variant=wine_variant,
        )

    def evaluate(
        self,
        *,
        country: str,
        grapes: Mapping[str, float] | Sequence[str] | str,
        label_scope: str,
        vintage_year: int = 2023,
        appellation: str | None = None,
        region: str | None = None,
        sub_region: str | None = None,
        commune: str | None = None,
        experimental: bool = False,
        wine_variant: str | None = None,
    ) -> OriginDecision:
        scope = label_scope.strip().casefold()
        if scope != "regulated_gi":
            return super().evaluate(
                country=country,
                grapes=grapes,
                label_scope=label_scope,
                vintage_year=vintage_year,
                appellation=appellation,
                region=region,
                sub_region=sub_region,
                commune=commune,
                experimental=experimental,
            )

        spec = self.resolve_legal_spec(
            country=country,
            appellation=appellation,
            region=region,
            sub_region=sub_region,
            commune=commune,
            wine_variant=wine_variant,
        )
        if spec is None:
            return super().evaluate(
                country=country,
                grapes=grapes,
                label_scope=label_scope,
                vintage_year=vintage_year,
                appellation=appellation,
                region=region,
                sub_region=sub_region,
                commune=commune,
                experimental=experimental,
            )

        blend, issues = self._blend(grapes)
        canonical = tuple(self.canonical_grape(name) for name, _ in blend)
        if issues:
            return OriginDecision(
                eligible=False,
                status="invalid_blend",
                label_scope=scope,
                canonical_grapes=canonical,
                rule_id=spec.id,
                issues=tuple(issues),
            )

        legal = self.legal_specs.evaluate_blend(
            spec,
            grapes,
            canonicalize=self.canonical_grape,
            same_grape=self.same_grape,
        )
        if not legal.eligible:
            return OriginDecision(
                eligible=False,
                status=legal.status,
                label_scope=scope,
                canonical_grapes=canonical,
                rule_id=spec.id,
                issues=legal.issues,
                warnings=legal.warnings,
                evidence=legal.evidence,
            )
        warnings = list(legal.warnings)
        if experimental:
            warnings.append(
                "An experimental flag cannot waive the sourced protected-origin specification."
            )
        return OriginDecision(
            eligible=True,
            status="appellation_eligible_sourced_spec",
            label_scope=scope,
            canonical_grapes=canonical,
            rule_id=spec.id,
            warnings=tuple(warnings),
            evidence=legal.evidence,
        )

    def stats(self) -> dict[str, int]:
        stats = super().stats()
        stats.update(self.legal_specs.stats())
        return stats
