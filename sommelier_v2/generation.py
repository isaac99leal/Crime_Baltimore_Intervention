"""Constrained wine-generation spine for Sommelier Simulator v2.

This module is the safe path from knowledge evidence to a game-facing WineRecord.
It does not invent legal authority. Origin legality is resolved first; named-site
label use is resolved separately; vintage and fermentation evidence can enrich a
legal record but can never override an origin rejection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .domain import WineRecord, WineStyle
from .knowledge.fermentation_guidance import (
    FermentationGuidance,
    assess_alcoholic_fermentation,
    assess_malolactic_conditions,
)
from .knowledge.fermentation_process import FermentationPlan, MustComposition
from .knowledge.origin_factory import ConstrainedOrigin, OriginRequest, WineOriginFactory
from .knowledge.vintage_engine import DailyWeather
from .knowledge.vintage_indices import VintageClimateIndices, calculate_vintage_climate_indices


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
    vintage_indices: VintageClimateIndices | None = None
    alcoholic_fermentation_guidance: FermentationGuidance | None = None
    malolactic_guidance: FermentationGuidance | None = None


@dataclass(frozen=True)
class GeneratedWine:
    wine: WineRecord
    origin: ConstrainedOrigin
    evidence: GenerationEvidence


class ConstrainedWineBuilder:
    """Build game-facing wine records only after the evidence gates pass."""

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

        # Origin is deliberately first. If it fails, no amount of vintage or
        # cellar detail can create the protected-origin wine.
        origin = self.origin_factory.create(request.origin)

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
        vineyard_label = (
            physical_site_name
            if physical_site_name and origin.site_claim_eligible
            else ""
        )

        wine = WineRecord(
            id=request.id,
            producer=request.producer,
            label=request.label,
            country=origin.country,
            region=origin.region,
            subregion=origin.sub_region or "",
            appellation=origin.appellation or "",
            vineyard=vineyard_label,
            vintage=request.origin.vintage_year,
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
            vintage_indices=vintage_indices,
            alcoholic_fermentation_guidance=alcoholic_guidance,
            malolactic_guidance=mlf_guidance,
        )
        return GeneratedWine(wine=wine, origin=origin, evidence=evidence)
