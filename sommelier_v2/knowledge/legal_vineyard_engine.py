"""Legal-spec-aware vineyard simulation.

The base vineyard engine handles physical block/vintage mechanics. This wrapper
makes sourced protected-origin specifications the default authority, applies
strict vineyard/wine-yield and minimum-potential-alcohol limits, applies separately
sourced machine-observable vineyard-law constraints, and evaluates whether a
named site can be used as a legal label claim.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .legal_rules import LegalAwareRegionGrapeRulebook
from .regional_rules import RegionGrapeRulebook
from .site_claims import SiteClaimRegistry
from .vineyard_engine import VineyardBlock, VineyardEngine as BaseVineyardEngine, VineyardOutcome
from .vineyard_legal_constraints import VineyardLegalConstraintRegistry
from .vineyard_registry import NamedSite, WorldWineKnowledgeCatalog
from .vintage_engine import DailyWeather


class LegalVineyardEngine(BaseVineyardEngine):
    def __init__(
        self,
        *,
        catalog: WorldWineKnowledgeCatalog | None = None,
        rulebook: RegionGrapeRulebook | None = None,
        sites: Iterable[NamedSite] | None = None,
        site_claims: SiteClaimRegistry | None = None,
        vineyard_constraints: VineyardLegalConstraintRegistry | None = None,
    ) -> None:
        catalog = catalog or WorldWineKnowledgeCatalog()
        rulebook = rulebook or LegalAwareRegionGrapeRulebook(catalog=catalog)
        super().__init__(catalog=catalog, rulebook=rulebook, sites=sites)
        self.site_claims = site_claims or SiteClaimRegistry()
        self.vineyard_constraints = vineyard_constraints or VineyardLegalConstraintRegistry(
            legal_specs=rulebook.legal_specs if isinstance(rulebook, LegalAwareRegionGrapeRulebook) else None
        )

    def simulate(
        self,
        block: VineyardBlock,
        weather_days: list[DailyWeather],
        *,
        vintage_year: int,
    ) -> VineyardOutcome:
        result = super().simulate(block, weather_days, vintage_year=vintage_year)
        if block.label_scope.casefold() != "regulated_gi":
            return replace(result, site_claim_eligible=False)
        if not isinstance(self.rulebook, LegalAwareRegionGrapeRulebook):
            return replace(result, site_claim_eligible=False)

        site = self.site_registry.resolve(site_id=block.site_id) if block.site_id else None
        appellation = block.appellation or (site.parent if site else None)
        spec = self.rulebook.resolve_legal_spec(
            country=block.country,
            appellation=appellation,
            region=block.region,
            wine_variant=block.wine_variant,
        )
        if spec is None:
            return replace(result, site_claim_eligible=False)

        issues = list(result.issues)
        warnings = list(result.warnings)
        label_eligible = result.label_eligible

        if spec.max_yield_t_ha is not None and result.yield_t_ha > spec.max_yield_t_ha + 1e-9:
            label_eligible = False
            issues.append(
                f"Yield {result.yield_t_ha:.2f} t/ha exceeds sourced {spec.appellation} maximum {spec.max_yield_t_ha:.2f} t/ha."
            )
        if spec.max_yield_hl_ha is not None and result.yield_hl_ha > spec.max_yield_hl_ha + 1e-9:
            label_eligible = False
            issues.append(
                f"Wine yield {result.yield_hl_ha:.2f} hL/ha exceeds sourced {spec.appellation} maximum {spec.max_yield_hl_ha:.2f} hL/ha."
            )
        if (
            spec.min_potential_alcohol_pct is not None
            and result.potential_alcohol_pct + 1e-9 < spec.min_potential_alcohol_pct
        ):
            label_eligible = False
            issues.append(
                f"Potential alcohol {result.potential_alcohol_pct:.2f}% is below sourced {spec.appellation} minimum natural alcohol {spec.min_potential_alcohol_pct:.2f}%."
            )

        vineyard_constraint = self.vineyard_constraints.resolve(
            country=block.country,
            appellation=spec.appellation,
            variant=spec.variant,
        )
        if vineyard_constraint is not None:
            vineyard_law = self.vineyard_constraints.assess(
                country=block.country,
                appellation=spec.appellation,
                variant=spec.variant,
                vine_density_per_ha=block.vine_density_per_ha,
                irrigation_mm_per_week=block.irrigation_mm_per_week,
                planting_pattern=block.planting_pattern,
                row_spacing_m=block.row_spacing_m,
                vine_spacing_m=block.vine_spacing_m,
            )
            if vineyard_law.satisfied is False:
                label_eligible = False
                issues.extend(vineyard_law.issues)
            elif vineyard_law.satisfied is None:
                warnings.extend(vineyard_law.warnings)

        if spec.grape_to_wine_yield_pct is not None:
            warnings.append(
                f"Legal grape-to-wine yield ceiling is {spec.grape_to_wine_yield_pct:g}%; enforce it at pressing/vinification, not vineyard harvest."
            )
        if spec.max_residual_sugar_g_l is not None or spec.max_malic_acid_g_l is not None:
            warnings.append(
                "Finished-wine sugar and malic-acid limits are enforced at the constrained wine/release stage, not at grape harvest."
            )

        site_claim = self.site_claims.evaluate(
            site=site,
            origin_decision=result.origin_decision,
            appellation=appellation,
            wine_variant=block.wine_variant,
        )
        site_claim_eligible = bool(site_claim.eligible and label_eligible)
        if site is not None and not site_claim_eligible:
            warnings.append(f"Named-site label claim remains unavailable: {site_claim.status}.")

        return replace(
            result,
            label_eligible=label_eligible,
            site_claim_eligible=site_claim_eligible,
            issues=tuple(issues),
            warnings=tuple(warnings),
        )
