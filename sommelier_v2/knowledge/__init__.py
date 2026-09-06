"""Provenance-aware wine knowledge layer for Sommelier Simulator v2."""

from .aging import modified_archetype, state_at_age
from .bottle_lifecycle import BottleAgingPlan, BottleAgingResult, BottleLifecycleConstraintError, age_cellar_wine
from .catalog import SOURCES, WineKnowledgeCatalog, normalize_name
from .cellar_pipeline import CellarHandoffInputs, CellarPipelineConstraintError, CellarPipelinePlan, CellarPipelineResult, run_cellar_pipeline
from .decision_runtime import DecisionRuntimeApplication, DecisionRuntimeError, DecisionRuntimeInputs, DecisionRuntimeResult, OXYGEN_MANAGEMENT_PRIORS, apply_winemaking_decisions
from .eu_promotions import EuCompositionDecision, EuLegalPromotionRegistry, VerificationLevel
from .expanded_catalog import CommercialObservation, NamedSite, PiwiRecord, VarietyAreaObservation, WorldWineKnowledgeCatalog
from .extraction_process import CapManagementEvent, ExtractionConstraintError, ExtractionPlan, ExtractionPoint, ExtractionResult, simulate_extraction
from .fermentation_chemistry import NutrientTimingEffect, ProcessChemistryAssessment, assess_process_chemistry, initial_microbiological_risk, molecular_so2_mg_l, nutrient_timing_effect, post_fermentation_microbiological_risk, white_juice_solids_risk
from .fermentation_engine import AlcoholicFermentationParams, FermentationState, MalolacticParams, MalolacticState, initial_state, run_alcoholic_fermentation, run_malolactic, step_alcoholic_fermentation, step_malolactic, temperature_control_target
from .fermentation_process import FermentationConstraintError, FermentationPlan, FermentationResult, MustComposition, NutrientAddition, run_fermentation, validate_must, validate_plan
from .finished_wine import FinishedWineAssembler, FinishedWineConstraintError, ValidatedWineRecord
from .harvest_lot import lot_from_harvest_must
from .harvest_must import HarvestMustConstraintError, HarvestMustPlan, HarvestMustProfile, must_from_vineyard, validate_harvest_must_plan
from .historical_vintages import AuthorityVintageRating, HistoricalVintageArchive, HistoricalVintageError, HistoricalVintageObservation, HistoricalVintageRegistry, HistoricalVintageSignal, HistoricalVintageStats, load_historical_vintages
from .jurisdiction_labels import BlendComponent, JurisdictionLabelValidator, LabelClaimDecision, LabelClaims
from .legal_practice_bridge import LegalPracticeAssessment, LegalPracticeBridge
from .legal_rules import LegalAwareRegionGrapeRulebook
from .legal_sources import LegalSourceRecord, LegalSourceRegistry
from .legal_specs import GrapeConstraint, LegalSpecDecision, LegalSpecRegistry, LegalWineSpec, ReleaseDecision
from .legal_vineyard_engine import LegalVineyardEngine
from .machine_legal_constraints import MachineConstraintDecision, MachineLegalConstraint, MachineLegalConstraintRegistry
from .maturation_process import BatonnageEvent, MaturationConstraintError, MaturationInput, MaturationPlan, MaturationResult, MaturationState, OxygenAddition, ToppingEvent, simulate_maturation
from .national_overrides import NationalAwareLegalSpecRegistry, NationalLegalOverrideRegistry, NationalOverrideDecision
from .origin_factory import ConstrainedOrigin, OriginRequest, WineOriginFactory
from .packaging import PackagingAssessment, PackagingConstraintError, PackagingPlan, assess_packaging
from .priors import SimulationPriors
from .process_chemistry_evidence import ChemistryEvidenceRecord, ChemistryEvidenceSource, ChemistryEvidenceStats, MODEL_EVIDENCE_LINKS, ModelEvidenceLink, ProcessChemistryEvidenceError, ProcessChemistryEvidenceRegistry, load_process_chemistry_evidence
from .regional_rules import OriginConstraintError, OriginDecision, RegionGrapeRulebook, RegionRule
from .release_runtime import ReleaseRuntimeConstraintError, ReleaseRuntimeInputs, validate_cellar_release
from .schema import *  # noqa: F401,F403 - package intentionally exposes schema types
from .site_research import MicroSiteObservation, SiteDataQualityFlag, SiteResearchError, SiteResearchRecord, SiteResearchRegistry, SiteResearchSource, SiteResearchStats, load_site_research
from .smoke_taint import SmokeMarkerAssessment, SmokeMarkerResult, SmokeTaintConstraintError, assess_smoke_markers, supported_smoke_guide_cultivars
from .trade_research import TradeFieldPolicy, TradeObservationConflict, TradeResearchError, TradeResearchRegistry, TradeResearchStats, TradeSourceRecord, TradeTechnicalObservation, load_trade_research
from .vineyard_engine import SiteRegistry, VineyardBlock, VineyardEngine as BaseVineyardEngine, VineyardOutcome
from .vintage import load_legacy_vintage_knowledge, vintage_stats
from .vintage_engine import DailyWeather, VintageDayState, VintageModelParams, VintageOutcome, simulate_vintage
from .winemaking_decisions import DecisionAuthorityAssessment, DecisionEvidenceSource, DecisionOption, WinemakingDecision, WinemakingDecisionError, WinemakingDecisionRegistry, WinemakingDecisionStats, load_winemaking_decisions
from .winery_provenance import LotBalance, LotMovement, ProvenanceSlice, WineryLot, WineryProvenanceError, WineryProvenanceLedger

VineyardEngine = LegalVineyardEngine

__all__ = [
    "SOURCES", "AlcoholicFermentationParams", "AuthorityVintageRating", "BaseVineyardEngine",
    "BatonnageEvent", "BlendComponent", "BottleAgingPlan", "BottleAgingResult",
    "BottleLifecycleConstraintError", "CapManagementEvent", "CellarHandoffInputs",
    "CellarPipelineConstraintError", "CellarPipelinePlan", "CellarPipelineResult",
    "ChemistryEvidenceRecord", "ChemistryEvidenceSource", "ChemistryEvidenceStats", "CommercialObservation",
    "ConstrainedOrigin", "DailyWeather", "DecisionAuthorityAssessment", "DecisionEvidenceSource",
    "DecisionOption", "DecisionRuntimeApplication", "DecisionRuntimeError", "DecisionRuntimeInputs",
    "DecisionRuntimeResult", "EuCompositionDecision", "EuLegalPromotionRegistry", "ExtractionConstraintError",
    "ExtractionPlan", "ExtractionPoint", "ExtractionResult", "FermentationConstraintError", "FermentationPlan",
    "FermentationResult", "FermentationState", "FinishedWineAssembler", "FinishedWineConstraintError",
    "GrapeConstraint", "HarvestMustConstraintError", "HarvestMustPlan", "HarvestMustProfile",
    "HistoricalVintageArchive", "HistoricalVintageError", "HistoricalVintageObservation",
    "HistoricalVintageRegistry", "HistoricalVintageSignal", "HistoricalVintageStats",
    "JurisdictionLabelValidator", "LabelClaimDecision", "LabelClaims", "LegalAwareRegionGrapeRulebook",
    "LegalPracticeAssessment", "LegalPracticeBridge", "LegalSourceRecord", "LegalSourceRegistry",
    "LegalSpecDecision", "LegalSpecRegistry", "LegalVineyardEngine", "LegalWineSpec", "LotBalance",
    "LotMovement", "MODEL_EVIDENCE_LINKS", "MachineConstraintDecision", "MachineLegalConstraint",
    "MachineLegalConstraintRegistry", "MalolacticParams", "MalolacticState", "MaturationConstraintError",
    "MaturationInput", "MaturationPlan", "MaturationResult", "MaturationState", "MicroSiteObservation",
    "ModelEvidenceLink", "MustComposition", "NamedSite", "NationalAwareLegalSpecRegistry",
    "NationalLegalOverrideRegistry", "NationalOverrideDecision", "NutrientAddition", "NutrientTimingEffect",
    "OXYGEN_MANAGEMENT_PRIORS", "OriginConstraintError", "OriginDecision", "OriginRequest",
    "OxygenAddition", "PackagingAssessment", "PackagingConstraintError", "PackagingPlan", "PiwiRecord",
    "ProcessChemistryAssessment", "ProcessChemistryEvidenceError", "ProcessChemistryEvidenceRegistry",
    "ProvenanceSlice", "RegionGrapeRulebook", "RegionRule", "ReleaseDecision", "ReleaseRuntimeConstraintError",
    "ReleaseRuntimeInputs", "SimulationPriors", "SiteDataQualityFlag", "SiteRegistry", "SiteResearchError",
    "SiteResearchRecord", "SiteResearchRegistry", "SiteResearchSource", "SiteResearchStats",
    "SmokeMarkerAssessment", "SmokeMarkerResult", "SmokeTaintConstraintError", "ToppingEvent",
    "TradeFieldPolicy", "TradeObservationConflict", "TradeResearchError", "TradeResearchRegistry",
    "TradeResearchStats", "TradeSourceRecord", "TradeTechnicalObservation", "ValidatedWineRecord",
    "VarietyAreaObservation", "VerificationLevel", "VineyardBlock", "VineyardEngine", "VineyardOutcome",
    "VintageDayState", "VintageModelParams", "VintageOutcome", "WineKnowledgeCatalog", "WineOriginFactory",
    "WinemakingDecision", "WinemakingDecisionError", "WinemakingDecisionRegistry", "WinemakingDecisionStats",
    "WineryLot", "WineryProvenanceError", "WineryProvenanceLedger", "WorldWineKnowledgeCatalog",
    "age_cellar_wine", "apply_winemaking_decisions", "assess_packaging", "assess_process_chemistry",
    "assess_smoke_markers", "initial_microbiological_risk", "initial_state", "load_historical_vintages",
    "load_legacy_vintage_knowledge", "load_process_chemistry_evidence", "load_site_research",
    "load_trade_research", "load_winemaking_decisions", "lot_from_harvest_must", "modified_archetype",
    "molecular_so2_mg_l", "must_from_vineyard", "normalize_name", "nutrient_timing_effect",
    "post_fermentation_microbiological_risk", "run_alcoholic_fermentation", "run_cellar_pipeline",
    "run_fermentation", "run_malolactic", "simulate_extraction", "simulate_maturation", "simulate_vintage",
    "state_at_age", "step_alcoholic_fermentation", "step_malolactic", "supported_smoke_guide_cultivars",
    "temperature_control_target", "validate_cellar_release", "validate_harvest_must_plan", "validate_must",
    "validate_plan", "vintage_stats", "white_juice_solids_risk",
]
