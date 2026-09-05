"""Provenance-aware wine knowledge layer for Sommelier Simulator v2."""

from .aging import modified_archetype, state_at_age
from .catalog import SOURCES, WineKnowledgeCatalog, normalize_name
from .expanded_catalog import CommercialObservation, NamedSite, PiwiRecord, VarietyAreaObservation, WorldWineKnowledgeCatalog
from .fermentation_engine import AlcoholicFermentationParams, FermentationState, MalolacticParams, MalolacticState, initial_state, run_alcoholic_fermentation, run_malolactic, step_alcoholic_fermentation, step_malolactic
from .fermentation_process import FermentationConstraintError, FermentationPlan, FermentationResult, MustComposition, NutrientAddition, run_fermentation, validate_must, validate_plan
from .legal_rules import LegalAwareRegionGrapeRulebook
from .legal_specs import GrapeConstraint, LegalSpecDecision, LegalSpecRegistry, LegalWineSpec, ReleaseDecision
from .origin_factory import ConstrainedOrigin, OriginRequest, WineOriginFactory
from .priors import SimulationPriors
from .regional_rules import OriginConstraintError, OriginDecision, RegionGrapeRulebook, RegionRule
from .schema import *  # noqa: F401,F403 - package intentionally exposes schema types
from .vineyard_engine import SiteRegistry, VineyardBlock, VineyardEngine, VineyardOutcome
from .vintage import load_legacy_vintage_knowledge, vintage_stats
from .vintage_engine import DailyWeather, VintageDayState, VintageModelParams, VintageOutcome, simulate_vintage

__all__ = [
    "SOURCES", "AlcoholicFermentationParams", "CommercialObservation", "ConstrainedOrigin",
    "DailyWeather", "FermentationConstraintError", "FermentationPlan", "FermentationResult",
    "FermentationState", "GrapeConstraint", "LegalAwareRegionGrapeRulebook", "LegalSpecDecision",
    "LegalSpecRegistry", "LegalWineSpec", "MalolacticParams", "MalolacticState", "MustComposition",
    "NamedSite", "NutrientAddition", "OriginConstraintError", "OriginDecision", "OriginRequest",
    "PiwiRecord", "RegionGrapeRulebook", "RegionRule", "ReleaseDecision", "SimulationPriors",
    "SiteRegistry", "VarietyAreaObservation", "VineyardBlock", "VineyardEngine", "VineyardOutcome",
    "VintageDayState", "VintageModelParams", "VintageOutcome", "WineKnowledgeCatalog",
    "WineOriginFactory", "WorldWineKnowledgeCatalog", "initial_state", "load_legacy_vintage_knowledge",
    "modified_archetype", "normalize_name", "run_alcoholic_fermentation", "run_fermentation",
    "run_malolactic", "simulate_vintage", "state_at_age", "step_alcoholic_fermentation",
    "step_malolactic", "validate_must", "validate_plan", "vintage_stats",
]
