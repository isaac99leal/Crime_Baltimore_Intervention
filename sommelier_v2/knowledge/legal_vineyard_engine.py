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
from .vineyard_yield_adjustments import VineyardYieldAdjustmentRegistry
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
        vineyard_yield_adjustments: VineyardYieldAdjustmentRegistry | None = None,
    ) -> None:
        catalog = catalog or WorldWineKnowledgeCatalog()
        rulebook = rulebook or LegalAwareRegionGrapeRulebook(catalog=catalog)
        super().__init__(catalog=catalog, rulebook=rulebook, sites=sites)
        self.site_claims = site_claims or SiteClaimRegistry()
        legal_specs = rulebook.legal_specs if isinstance(rulebook, LegalAwareRegionGrapeRulebook) else None
        self.vineyard_constraints = vineyard_constraints or VineyardLegalConstraintRegistry(legal_specs=legal_specs)
        self.vineyard_yield_adjustments = vineyard_yield_adjustments or VineyardYieldAdjustmentRegistry(legal_specs=legal_specs)

    def simulate(self, block: VineyardBlock, weather_days: list[DailyWeather], *, vintage_year: int) -> VineyardOutcome:
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
            issues.append(f"Yield {result.yield_t_ha:.2f} t/ha exceeds sourced {spec.appellation} maximum {spec.max_yield_t_ha:.2f} t/ha.")
        if spec.max_yield_hl_ha is not None and result.yield_hl_ha > spec.max_yield_hl_ha + 1e-9:
            label_eligible = False
            issues.append(f"Wine yield {result.yield_hl_ha:.2f} hL/ha exceeds sourced {spec.appellation} maximum {spec.max_yield_hl_ha:.2f} hL/ha.")
        if spec.min_potential_alcohol_pct is not None and result.potential_alcohol_pct + 1e-9 < spec.min_potential_alcohol_pct:
            label_eligible = False
            issues.append(f"Potential alcohol {result.potential_alcohol_pct:.2f}% is below sourced {spec.appellation} minimum natural alcohol {spec.min_potential_alcohol_pct:.2f}%.")

        vineyard_constraint = self.vineyard_constraints.resolve(country=block.country, appellation=spec.appellation, variant=spec.variant)
        if vineyard_constraint is not None:
            vineyard_law = self.vineyard_constraints.assess(
                country=block.country,
                appellation=spec.appellation,
                variant=spec.variant,
                wine_style=spec.wine_style,
                vine_density_per_ha=block.vine_density_per_ha,
                irrigation_mm_per_week=block.irrigation_mm_per_week,
                planting_pattern=block.planting_pattern,
                row_spacing_m=block.row_spacing_m,
                vine_spacing_m=block.vine_spacing_m,
                pruning_system=block.pruning_system,
                retained_buds_per_vine=block.retained_buds_per_vine,
                fruiting_shoots_per_vine=block.fruiting_shoots_per_vine,
                support_system=block.support_system,
                canopy_height_m=block.canopy_height_m,
                parcel_crop_load_kg_ha=block.parcel_crop_load_kg_ha,
            )
            if vineyard_law.satisfied is False:
                label_eligible = False
                issues.extend(vineyard_law.issues)
                warnings.extend(vineyard_law.warnings)
            elif vineyard_law.satisfied is None:
                label_eligible = False
                warnings.extend(vineyard_law.warnings)
                warnings.append(f"Protected-origin vineyard compliance is unresolved under {vineyard_law.constraint_id}; the label claim is withheld until required measurements are supplied.")

        yield_rule = self.vineyard_yield_adjustments.resolve(country=block.country, appellation=spec.appellation, variant=spec.variant)
        if yield_rule is not None:
            yield_adjustment = self.vineyard_yield_adjustments.assess(
                country=block.country,
                appellation=spec.appellation,
                variant=spec.variant,
                dead_missing_vine_fraction=block.dead_missing_vine_fraction,
            )
            if yield_adjustment.multiplier is None:
                label_eligible = False
                warnings.extend(yield_adjustment.warnings)
                warnings.append(f"Protected-origin yield adjustment is unresolved under {yield_adjustment.rule_id}; the label claim is withheld until the dead/missing-vine fraction is supplied.")
            elif yield_adjustment.multiplier < 1.0 - 1e-12:
                if spec.max_yield_hl_ha is None:
                    label_eligible = False
                    warnings.append(f"{yield_adjustment.rule_id} requires a proportional authorized-yield reduction, but no executable hL/ha parent yield is available.")
                else:
                    adjusted_yield = spec.max_yield_hl_ha * yield_adjustment.multiplier
                    warnings.append(f"Dead/missing vines reduce the sourced {spec.appellation} authorized yield from {spec.max_yield_hl_ha:g} to {adjusted_yield:.2f} hL/ha under {yield_adjustment.rule_id}.")
                    if result.yield_hl_ha > adjusted_yield + 1e-9:
                        label_eligible = False
                        issues.append(f"Wine yield {result.yield_hl_ha:.2f} hL/ha exceeds the dead/missing-vine-adjusted {spec.appellation} maximum of {adjusted_yield:.2f} hL/ha.")

        if spec.grape_to_wine_yield_pct is not None:
            warnings.append(f"Legal grape-to-wine yield ceiling is {spec.grape_to_wine_yield_pct:g}%; enforce it at pressing/vinification, not vineyard harvest.")
        if spec.max_residual_sugar_g_l is not None or spec.max_malic_acid_g_l is not None:
            warnings.append("Finished-wine sugar and malic-acid limits are enforced at the constrained wine/release stage, not at grape harvest.")

        site_claim = self.site_claims.evaluate(site=site, origin_decision=result.origin_decision, appellation=appellation, wine_variant=block.wine_variant)
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
