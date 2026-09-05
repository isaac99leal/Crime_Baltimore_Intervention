"""Constrained wine-generation spine for Sommelier Simulator v2.

This module is the safe path from knowledge evidence to a game-facing WineRecord.
It does not invent legal authority. Origin legality is resolved first; named-site
label use is resolved separately; protected-origin production and release rules
are validated before a record can enter an authoritative catalog; vintage and
fermentation evidence can enrich a legal record but can never override a legal
rejection.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from .domain import WineRecord, WineStyle
from .knowledge.catalog import normalize_name
from .knowledge.fermentation_guidance import (
    FermentationGuidance,
    assess_alcoholic_fermentation,
    assess_malolactic_conditions,
)
from .knowledge.fermentation_process import FermentationPlan, MustComposition
from .knowledge.legal_rules import LegalAwareRegionGrapeRulebook
from .knowledge.origin_factory import ConstrainedOrigin, OriginRequest, WineOriginFactory
from .knowledge.regional_rules import OriginConstraintError
from .knowledge.vintage_engine import DailyWeather
from .knowledge.vintage_indices import VintageClimateIndices, calculate_vintage_climate_indices


class WineProductionConstraintError(ValueError):
    """Raised when a protected-origin wine fails modeled production rules."""


class WineReleaseConstraintError(ValueError):
    """Raised when a protected-origin wine fails modeled release rules."""


@dataclass(frozen=True)
class WineBuildRequest:
    id: str
    producer: str
    label: str
    origin: OriginRequest
    style: WineStyle = WineStyle.OTHER
    classification: str = ""
    wholesale_cost: float = 0.0
    rarity: float = 0.0
    winemaking_notes: str = ""
    farming_notes: str = ""
    drink_window_start: int = 0
    drink_window_end: int = 0
    acidity: float = 3.0
    tannin: float = 3.0
    body: float = 3.0
    sweetness: float = 1.0
    alcohol: float = 13.0
    fruit_intensity: float = 3.0
    earth_intensity: float = 2.0
    oak_influence: float = 2.0
    aromas: tuple[str, ...] = ()
    is_organic: bool = False
    is_biodynamic: bool = False
    is_natural: bool = False
    is_ungrafted: bool = False
    is_old_vine: bool = False

    # Machine-modeled legal production/release facts. These remain distinct from
    # sensory fields. For example, ``acidity`` above is a 1..5 tasting-scale value;
    # ``total_acidity_g_l`` below is a measured legal chemistry value.
    vineyard_yield_t_ha: float | None = None
    wine_yield_hl_ha: float | None = None
    actual_grape_to_wine_yield_pct: float | None = None
    must_sugar_g_l: float | None = None
    potential_alcohol_pct: float | None = None
    bottled_in_origin: bool | None = None
    total_aging_months: int | None = None
    wood_aging_months: int = 0
    bottle_aging_months: int = 0
    method: str | None = None
    manual_harvest: bool | None = None
    total_alcohol_pct: float | None = None
    total_acidity_g_l: float | None = None
    dry_extract_g_l: float | None = None
    residual_sugar_g_l: float | None = None
    malic_acid_g_l: float | None = None
    elevage_end_year: int | None = None
    elevage_end_month: int | None = None
    elevage_end_day: int | None = None
    release_year: int | None = None
    release_month: int | None = None
    release_day: int | None = None


@dataclass(frozen=True)
class GenerationEvidence:
    origin_status: str
    origin_rule_id: str | None
    origin_evidence: tuple[str, ...]
    physical_site_id: str | None
    physical_site_name: str | None
    site_claim_eligible: bool
    site_claim_status: str
    site_claim_rule_id: str | None
    site_claim_evidence: tuple[str, ...]
    site_claim_name: str | None = None
    legal_spec_id: str | None = None
    production_status: str = "not_applicable"
    release_status: str = "not_applicable"
    legal_model_notes: str = ""
    vintage_indices: VintageClimateIndices | None = None
    alcoholic_fermentation_guidance: FermentationGuidance | None = None
    malolactic_guidance: FermentationGuidance | None = None


@dataclass(frozen=True)
class GeneratedWine:
    wine: WineRecord
    origin: ConstrainedOrigin
    evidence: GenerationEvidence


class ConstrainedWineBuilder:
    """Build game-facing wine records only after all modeled evidence gates pass."""

    def __init__(self, *, origin_factory: WineOriginFactory | None = None) -> None:
        self.origin_factory = origin_factory or WineOriginFactory()

    @staticmethod
    def _validate_commercial_fields(request: WineBuildRequest) -> None:
        if not request.id.strip():
            raise ValueError("Wine id is required")
        if not request.producer.strip():
            raise ValueError("Producer is required")
        if not request.label.strip():
            raise ValueError("Wine label is required")
        if request.wholesale_cost < 0.0:
            raise ValueError("Wholesale cost cannot be negative")
        if not 0.0 <= request.rarity <= 1.0:
            raise ValueError("Rarity must be within 0..1")
        if request.drink_window_start < 0 or request.drink_window_end < 0:
            raise ValueError("Drink-window offsets cannot be negative")
        if request.drink_window_end and request.drink_window_start > request.drink_window_end:
            raise ValueError("Drink-window start cannot be after drink-window end")
        if request.total_aging_months is not None and request.total_aging_months < 0:
            raise ValueError("Total aging months cannot be negative")
        if request.wood_aging_months < 0 or request.bottle_aging_months < 0:
            raise ValueError("Wood and bottle aging months cannot be negative")
        for name, value in (
            ("vineyard_yield_t_ha", request.vineyard_yield_t_ha),
            ("wine_yield_hl_ha", request.wine_yield_hl_ha),
            ("actual_grape_to_wine_yield_pct", request.actual_grape_to_wine_yield_pct),
            ("must_sugar_g_l", request.must_sugar_g_l),
            ("potential_alcohol_pct", request.potential_alcohol_pct),
            ("total_alcohol_pct", request.total_alcohol_pct),
            ("total_acidity_g_l", request.total_acidity_g_l),
            ("dry_extract_g_l", request.dry_extract_g_l),
            ("residual_sugar_g_l", request.residual_sugar_g_l),
            ("malic_acid_g_l", request.malic_acid_g_l),
        ):
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative")
        for name, value, low, high in (
            ("elevage_end_month", request.elevage_end_month, 1, 12),
            ("release_month", request.release_month, 1, 12),
            ("elevage_end_day", request.elevage_end_day, 1, 31),
            ("release_day", request.release_day, 1, 31),
        ):
            if value is not None and not low <= value <= high:
                raise ValueError(f"{name} must be within {low}..{high}")
        if (
            request.origin.producer
            and normalize_name(request.origin.producer) != normalize_name(request.producer)
        ):
            raise ValueError(
                "WineBuildRequest producer must match OriginRequest producer when both are supplied"
            )

    def _validate_regulated_production_and_release(
        self,
        *,
        request: WineBuildRequest,
        origin: ConstrainedOrigin,
        vintage_year: int,
    ) -> tuple[str | None, str, str, str]:
        if request.origin.label_scope.casefold() != "regulated_gi":
            return None, "not_applicable", "not_applicable", ""
        if not isinstance(self.origin_factory.rulebook, LegalAwareRegionGrapeRulebook):
            raise OriginConstraintError(
                "Protected-origin authoritative generation requires LegalAwareRegionGrapeRulebook"
            )

        rulebook = self.origin_factory.rulebook
        spec = rulebook.resolve_legal_spec(
            country=origin.country,
            appellation=origin.appellation,
            region=origin.region,
            sub_region=origin.sub_region,
            commune=origin.commune,
            wine_variant=request.origin.wine_variant,
        )
        if spec is None:
            raise OriginConstraintError(
                "Protected-origin wine passed origin validation without a resolvable strict legal specification"
            )

        production = rulebook.legal_specs.validate_production(
            spec,
            vineyard_yield_t_ha=request.vineyard_yield_t_ha,
            wine_yield_hl_ha=request.wine_yield_hl_ha,
            actual_grape_to_wine_yield_pct=request.actual_grape_to_wine_yield_pct,
            must_sugar_g_l=request.must_sugar_g_l,
            potential_alcohol_pct=request.potential_alcohol_pct,
            bottled_in_origin=request.bottled_in_origin,
            require_complete=True,
        )
        if not production.eligible:
            raise WineProductionConstraintError(
                "; ".join(production.issues) or "protected-origin production requirements not met"
            )

        release = rulebook.legal_specs.validate_release(
            spec,
            total_aging_months=request.total_aging_months or 0,
            wood_aging_months=request.wood_aging_months,
            bottle_aging_months=request.bottle_aging_months,
            method=request.method,
            manual_harvest=request.manual_harvest,
            final_alcohol_pct=request.alcohol,
            total_alcohol_pct=request.total_alcohol_pct,
            total_acidity_g_l=request.total_acidity_g_l,
            dry_extract_g_l=request.dry_extract_g_l,
            residual_sugar_g_l=request.residual_sugar_g_l,
            malic_acid_g_l=request.malic_acid_g_l,
            vintage_year=vintage_year,
            elevage_end_year=request.elevage_end_year,
            elevage_end_month=request.elevage_end_month,
            elevage_end_day=request.elevage_end_day,
            release_year=request.release_year,
            release_month=request.release_month,
            release_day=request.release_day,
            require_complete=True,
        )
        if not release.eligible:
            raise WineReleaseConstraintError(
                "; ".join(release.issues) or "protected-origin release requirements not met"
            )

        return (
            spec.id,
            "production_eligible_sourced_spec",
            "release_eligible_sourced_spec",
            spec.notes,
        )

    def build(
        self,
        request: WineBuildRequest,
        *,
        weather_days: Sequence[DailyWeather] | None = None,
        harvest_day: int | None = None,
        must: MustComposition | None = None,
        fermentation_plan: FermentationPlan | None = None,
        total_so2_mg_l: float | None = None,
    ) -> GeneratedWine:
        self._validate_commercial_fields(request)

        origin_request = request.origin
        if origin_request.producer is None:
            origin_request = replace(origin_request, producer=request.producer)

        # Legal origin precedes every physical or sensory enrichment step.
        origin = self.origin_factory.create(origin_request)
        legal_spec_id, production_status, release_status, legal_model_notes = (
            self._validate_regulated_production_and_release(
                request=request,
                origin=origin,
                vintage_year=origin_request.vintage_year,
            )
        )

        vintage_indices = None
        if weather_days is not None:
            vintage_indices = calculate_vintage_climate_indices(
                list(weather_days),
                harvest_day=harvest_day,
            )

        if (must is None) != (fermentation_plan is None):
            raise ValueError(
                "must and fermentation_plan must be supplied together when fermentation evidence is requested"
            )

        alcoholic_guidance = None
        mlf_guidance = None
        if must is not None and fermentation_plan is not None:
            alcoholic_guidance = assess_alcoholic_fermentation(must, fermentation_plan)
            mlf_guidance = assess_malolactic_conditions(
                must,
                fermentation_plan,
                estimated_alcohol_pct=request.alcohol,
                total_so2_mg_l=total_so2_mg_l,
            )

        physical_site_name = origin.site.name if origin.site is not None else None
        site_claim_name = origin.site_claim_name if origin.site_claim_eligible else None
        vineyard_label = site_claim_name or ""

        wine = WineRecord(
            id=request.id,
            producer=request.producer,
            label=request.label,
            country=origin.country,
            region=origin.region,
            subregion=origin.sub_region or "",
            appellation=origin.appellation or "",
            vineyard=vineyard_label,
            vintage=origin_request.vintage_year,
            style=request.style,
            grapes=origin.canonical_grapes,
            classification=request.classification,
            wholesale_cost=request.wholesale_cost,
            rarity=request.rarity,
            acidity=request.acidity,
            tannin=request.tannin,
            body=request.body,
            sweetness=request.sweetness,
            alcohol=request.alcohol,
            fruit_intensity=request.fruit_intensity,
            earth_intensity=request.earth_intensity,
            oak_influence=request.oak_influence,
            aromas=request.aromas,
            winemaking_notes=request.winemaking_notes,
            farming_notes=request.farming_notes,
            drink_window_start=request.drink_window_start,
            drink_window_end=request.drink_window_end,
            is_organic=request.is_organic,
            is_biodynamic=request.is_biodynamic,
            is_natural=request.is_natural,
            is_ungrafted=request.is_ungrafted,
            is_old_vine=request.is_old_vine,
        )

        evidence = GenerationEvidence(
            origin_status=origin.decision.status,
            origin_rule_id=origin.decision.rule_id,
            origin_evidence=origin.decision.evidence,
            physical_site_id=origin.site.id if origin.site is not None else None,
            physical_site_name=physical_site_name,
            site_claim_eligible=origin.site_claim_eligible,
            site_claim_status=origin.site_claim_status,
            site_claim_rule_id=origin.site_claim_rule_id,
            site_claim_evidence=origin.site_claim_evidence,
            site_claim_name=origin.site_claim_name,
            legal_spec_id=legal_spec_id,
            production_status=production_status,
            release_status=release_status,
            legal_model_notes=legal_model_notes,
            vintage_indices=vintage_indices,
            alcoholic_fermentation_guidance=alcoholic_guidance,
            malolactic_guidance=mlf_guidance,
        )
        return GeneratedWine(wine=wine, origin=origin, evidence=evidence)
