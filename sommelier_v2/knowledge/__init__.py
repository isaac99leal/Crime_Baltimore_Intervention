"""Provenance-aware wine knowledge layer for Sommelier Simulator v2."""

from .aging import modified_archetype, state_at_age
from .catalog import SOURCES, WineKnowledgeCatalog, normalize_name
from .eu_promotions import EuCompositionDecision, EuLegalPromotionRegistry, VerificationLevel
from .expanded_catalog import CommercialObservation, NamedSite, PiwiRecord, VarietyAreaObservation, WorldWineKnowledgeCatalog
from .fermentation_engine import AlcoholicFermentationParams, FermentationState, MalolacticParams, MalolacticState, initial_state, run_alcoholic_fermentation, run_malolactic, step_alcoholic_fermentation, step_malolactic
from .fermentation_process import FermentationConstraintError, FermentationPlan, FermentationResult, MustComposition, NutrientAddition, run_fermentation, validate_must, validate_plan
from .finished_wine import FinishedWineAssembler, FinishedWineConstraintError, ValidatedWineRecord
from .harvest_must import HarvestMustConstraintError, HarvestMustPlan, HarvestMustProfile, must_from_vineyard, validate_harvest_must_plan
from .historical_vintages import AuthorityVintageRating, HistoricalVintageArchive, HistoricalVintageError, HistoricalVintageObservation, HistoricalVintageRegistry, HistoricalVintageSignal, HistoricalVintageStats, load_historical_vintages
from .jurisdiction_labels import BlendComponent, JurisdictionLabelValidator, LabelClaimDecision, LabelClaims
from .legal_rules import LegalAwareRegionGrapeRulebook
from .legal_sources import LegalSourceRecord, LegalSourceRegistry
from .legal_specs import GrapeConstraint, LegalSpecDecision, LegalSpecRegistry, LegalWineSpec, ReleaseDecision
from .legal_vineyard_engine import LegalVineyardEngine
from .machine_legal_constraints import MachineConstraintDecision, MachineLegalConstraint, MachineLegalConstraintRegistry
from .national_overrides import NationalAwareLegalSpecRegistry, NationalLegalOverrideRegistry, NationalOverrideDecision
from .origin_factory import ConstrainedOrigin, OriginRequest, WineOriginFactory
from .priors import SimulationPriors
from .regional_rules import OriginConstraintError, OriginDecision, RegionGrapeRulebook, RegionRule
from .schema import *  # noqa: F401,F403 - package intentionally exposes schema types
from .vineyard_engine import SiteRegistry, VineyardBlock, VineyardEngine as BaseVineyardEngine, VineyardOutcome
from .vintage import load_legacy_vintage_knowledge, vintage_stats
from .vintage_engine import DailyWeather, VintageDayState, VintageModelParams, VintageOutcome, simulate_vintage
from .winery_provenance import ProvenanceSlice, WineryLot, WineryProvenanceError, WineryProvenanceLedger

VineyardEngine = LegalVineyardEngine

__all__ = [
    "SOURCES", "AlcoholicFermentationParams", "AuthorityVintageRating", "BaseVineyardEngine",
    "BlendComponent", "CommercialObservation", "ConstrainedOrigin", "DailyWeather",
    "EuCompositionDecision", "EuLegalPromotionRegistry", "FermentationConstraintError",
    "FermentationPlan", "FermentationResult", "FermentationState", "FinishedWineAssembler",
    "FinishedWineConstraintError", "GrapeConstraint", "HarvestMustConstraintError",
    "HarvestMustPlan", "HarvestMustProfile", "HistoricalVintageArchive", "HistoricalVintageError",
    "HistoricalVintageObservation", "HistoricalVintageRegistry", "HistoricalVintageSignal",
    "HistoricalVintageStats", "JurisdictionLabelValidator", "LabelClaimDecision", "LabelClaims",
    "LegalAwareRegionGrapeRulebook", "LegalSourceRecord", "LegalSourceRegistry", "LegalSpecDecision",
    "LegalSpecRegistry", "LegalVineyardEngine", "LegalWineSpec", "MachineConstraintDecision",
    "MachineLegalConstraint", "MachineLegalConstraintRegistry", "MalolacticParams", "MalolacticState",
    "MustComposition", "NamedSite", "NationalAwareLegalSpecRegistry", "NationalLegalOverrideRegistry",
    "NationalOverrideDecision", "NutrientAddition", "OriginConstraintError", "OriginDecision",
    "OriginRequest", "PiwiRecord", "ProvenanceSlice", "RegionGrapeRulebook", "RegionRule",
    "ReleaseDecision", "SimulationPriors", "SiteRegistry", "ValidatedWineRecord",
    "VarietyAreaObservation", "VerificationLevel", "VineyardBlock", "VineyardEngine",
    "VineyardOutcome", "VintageDayState", "VintageModelParams", "VintageOutcome",
    "WineKnowledgeCatalog", "WineOriginFactory", "WineryLot", "WineryProvenanceError",
    "WineryProvenanceLedger", "WorldWineKnowledgeCatalog", "initial_state",
    "load_historical_vintages", "load_legacy_vintage_knowledge", "modified_archetype",
    "must_from_vineyard", "normalize_name", "run_alcoholic_fermentation", "run_fermentation",
    "run_malolactic", "simulate_vintage", "state_at_age", "step_alcoholic_fermentation",
    "step_malolactic", "validate_harvest_must_plan", "validate_must", "validate_plan", "vintage_stats",
]
