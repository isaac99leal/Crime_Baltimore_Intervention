"""Legal-spec-aware origin rulebook.

The strict verified registry is the only layer that can positively authorize a
protected-origin wine. Bulk machine extraction is used as a negative guard and
as a bounded composition-evidence layer. A machine composition pass never
upgrades an unknown GI to fully eligible.
"""
from __future__ import annotations

from typing import Mapping, Sequence

from .eu_promotions import EuLegalPromotionRegistry
from .legal_specs import LegalSpecRegistry, LegalWineSpec
from .machine_legal_constraints import MachineLegalConstraintRegistry
from .national_overrides import NationalAwareLegalSpecRegistry
from .regional_rules import OriginDecision, RegionGrapeRulebook


class LegalAwareRegionGrapeRulebook(RegionGrapeRulebook):
    def __init__(
        self,
        *args,
        legal_specs: LegalSpecRegistry | NationalAwareLegalSpecRegistry | None = None,
        machine_constraints: MachineLegalConstraintRegistry | None = None,
        eu_promotions: EuLegalPromotionRegistry | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        # Default production path applies effective national-source precedence.
        # Tests/private callers that pass an explicit registry retain full control.
        self.legal_specs = legal_specs or NationalAwareLegalSpecRegistry()
        self.machine_constraints = machine_constraints or MachineLegalConstraintRegistry()
        self.eu_promotions = eu_promotions or EuLegalPromotionRegistry(self.machine_constraints)

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
            machine = self.machine_constraints.resolve(
                country=country,
                appellation=appellation,
                region=region,
                sub_region=sub_region,
                commune=commune,
            )
            promotion = None
            if machine is not None:
                denied = self.machine_constraints.evaluate_deny(
                    machine,
                    grapes,
                    canonicalize=self.canonical_grape,
                    same_grape=self.same_grape,
                )
                if denied.rejected:
                    blend, blend_issues = self._blend(grapes)
                    canonical = tuple(self.canonical_grape(name) for name, _ in blend)
                    return OriginDecision(
                        eligible=False,
                        status=denied.status,
                        label_scope=scope,
                        canonical_grapes=canonical,
                        rule_id=f"machine:{machine.gi_identifier}",
                        issues=tuple(blend_issues) + denied.issues,
                        warnings=(
                            "This rejection comes from a deny-safe machine extraction of an authoritative product specification. It is not positive GI certification.",
                        ),
                        evidence=denied.evidence,
                    )
                promotion = self.eu_promotions.evaluate_composition(
                    machine,
                    grapes,
                    canonicalize=self.canonical_grape,
                    same_grape=self.same_grape,
                )

            # The legacy regional rulebook is useful for canonicalization and
            # plausibility diagnostics, but it is never positive legal authority.
            # Returning an eligible legacy decision here would allow a stale or
            # hand-maintained allowed_grapes list to create a legally impossible GI.
            fallback = super().evaluate(
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
            if promotion is not None and promotion.verified:
                return OriginDecision(
                    eligible=False,
                    status="composition_verified_full_spec_pending",
                    label_scope=scope,
                    canonical_grapes=promotion.canonical_grapes,
                    rule_id=f"machine:{machine.gi_identifier}",
                    issues=(
                        "The grape-composition dimension is verified, but the full protected-origin production specification has not yet been promoted.",
                    ),
                    warnings=(
                        "Composition verification is not full GI certification; yield, process, aging, release, bottling, and other applicable requirements remain fail-closed.",
                    ),
                    evidence=promotion.evidence,
                )

            warnings = [
                "No reviewed strict product specification is available for positive protected-origin authorization.",
                "Legacy regional grape lists may support plausibility checks, but they cannot certify a protected-origin claim.",
            ]
            if fallback.status:
                warnings.append(f"Legacy diagnostic status: {fallback.status}.")
            return OriginDecision(
                eligible=False,
                status="strict_legal_spec_pending",
                label_scope=scope,
                canonical_grapes=fallback.canonical_grapes,
                rule_id=fallback.rule_id,
                issues=(
                    "Protected-origin generation is blocked until a reviewed strict legal specification is available.",
                ),
                warnings=tuple(warnings),
                evidence=fallback.evidence,
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
        stats.update(self.machine_constraints.stats())
        stats.update(self.eu_promotions.stats())
        return stats
