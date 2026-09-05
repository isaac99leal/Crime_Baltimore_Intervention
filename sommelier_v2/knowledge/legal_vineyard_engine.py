"""Legal-spec-aware vineyard simulation.

The base vineyard engine handles physical block/vintage mechanics and the legacy
geographic guard. This wrapper makes sourced protected-origin specifications the
default authority and applies vineyard-level yield and minimum-potential-alcohol
limits without pretending that final-wine chemistry is known at harvest.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .expanded_catalog import NamedSite, WorldWineKnowledgeCatalog
from .legal_rules import LegalAwareRegionGrapeRulebook
from .regional_rules import RegionGrapeRulebook
from .vineyard_engine import VineyardBlock, VineyardEngine as BaseVineyardEngine, VineyardOutcome
from .vintage_engine import DailyWeather


class LegalVineyardEngine(BaseVineyardEngine):
    def __init__(
        self,
        *,
        catalog: WorldWineKnowledgeCatalog | None = None,
        rulebook: RegionGrapeRulebook | None = None,
        sites: Iterable[NamedSite] | None = None,
    ) -> None:
        catalog = catalog or WorldWineKnowledgeCatalog()
        rulebook = rulebook or LegalAwareRegionGrapeRulebook(catalog=catalog)
        super().__init__(catalog=catalog, rulebook=rulebook, sites=sites)

    def simulate(
        self,
        block: VineyardBlock,
        weather_days: list[DailyWeather],
        *,
        vintage_year: int,
    ) -> VineyardOutcome:
        result = super().simulate(block, weather_days, vintage_year=vintage_year)
        if block.label_scope.casefold() != "regulated_gi":
            return result
        if not isinstance(self.rulebook, LegalAwareRegionGrapeRulebook):
            return result

        site = self.site_registry.resolve(site_id=block.site_id) if block.site_id else None
        appellation = block.appellation or (site.parent if site else None)
        spec = self.rulebook.resolve_legal_spec(
            country=block.country,
            appellation=appellation,
            region=block.region,
        )
        if spec is None:
            return result

        issues = list(result.issues)
        warnings = list(result.warnings)
        label_eligible = result.label_eligible

        if spec.max_yield_t_ha is not None and result.yield_t_ha > spec.max_yield_t_ha + 1e-9:
            label_eligible = False
            issues.append(
                f"Yield {result.yield_t_ha:.2f} t/ha exceeds sourced {spec.appellation} maximum {spec.max_yield_t_ha:.2f} t/ha."
            )
        if (
            spec.min_potential_alcohol_pct is not None
            and result.potential_alcohol_pct + 1e-9 < spec.min_potential_alcohol_pct
        ):
            label_eligible = False
            issues.append(
                f"Potential alcohol {result.potential_alcohol_pct:.2f}% is below sourced {spec.appellation} minimum natural alcohol {spec.min_potential_alcohol_pct:.2f}%."
            )
        if spec.grape_to_wine_yield_pct is not None:
            warnings.append(
                f"Legal grape-to-wine yield ceiling is {spec.grape_to_wine_yield_pct:g}%; enforce it at pressing/vinification, not vineyard harvest."
            )

        return replace(
            result,
            label_eligible=label_eligible,
            site_claim_eligible=bool(result.site_claim_eligible and label_eligible),
            issues=tuple(issues),
            warnings=tuple(warnings),
        )
