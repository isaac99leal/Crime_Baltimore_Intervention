"""Normalized wine-knowledge schema for Sommelier Simulator v2.

The schema separates three concerns:
1. factual identity/legal data with provenance;
2. researched or legacy-enriched grape/vintage attributes;
3. simulation priors used when real measurements are unavailable.

Unknown values remain ``None``. The engine must not turn missing facts into fake facts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CoverageLevel(str, Enum):
    IDENTITY = "identity"
    CORE = "core"
    DEEP = "deep"
    LEGACY_MIGRATED = "legacy_migrated"
    SIMULATION_PRIOR = "simulation_prior"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AUTHORITATIVE = "authoritative"


@dataclass(frozen=True)
class SourceRef:
    id: str
    authority: str
    title: str
    url: str
    retrieved_on: str
    confidence: Confidence = Confidence.HIGH
    notes: str = ""


@dataclass(frozen=True)
class NumericRange:
    low: float | None = None
    typical: float | None = None
    high: float | None = None
    unit: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        vals = [x for x in (self.low, self.typical, self.high) if x is not None]
        if len(vals) >= 2 and vals != sorted(vals):
            errors.append(f"range values are not ordered: {self}")
        return errors


@dataclass
class PhenologyProfile:
    budbreak_relative: float | None = None       # -1 early, 0 mid, +1 late
    flowering_relative: float | None = None
    veraison_relative: float | None = None
    harvest_relative: float | None = None
    growing_season_days: NumericRange = field(default_factory=NumericRange)
    heat_requirement_index: float | None = None
    frost_exposure_risk: float | None = None
    heat_spike_sensitivity: float | None = None


@dataclass
class ViticultureProfile:
    vigor_index: float | None = None
    yield_hl_ha: NumericRange = field(default_factory=lambda: NumericRange(unit="hL/ha"))
    berry_size_index: float | None = None
    bunch_compactness_index: float | None = None
    skin_to_pulp_index: float | None = None
    drought_tolerance: float | None = None
    water_stress_sensitivity: float | None = None
    acidity_retention: float | None = None
    sugar_accumulation: float | None = None
    phenolic_ripening_speed: float | None = None
    botrytis_susceptibility: float | None = None
    powdery_mildew_susceptibility: float | None = None
    downy_mildew_susceptibility: float | None = None
    rot_susceptibility: float | None = None
    preferred_climates: list[str] = field(default_factory=list)
    rootstock_notes: list[str] = field(default_factory=list)


@dataclass
class MustChemistryProfile:
    brix: NumericRange = field(default_factory=lambda: NumericRange(unit="°Bx"))
    potential_alcohol_pct: NumericRange = field(default_factory=lambda: NumericRange(unit="% abv"))
    ph: NumericRange = field(default_factory=NumericRange)
    titratable_acidity_g_l: NumericRange = field(default_factory=lambda: NumericRange(unit="g/L"))
    malic_acid_g_l: NumericRange = field(default_factory=lambda: NumericRange(unit="g/L"))
    tartaric_acid_g_l: NumericRange = field(default_factory=lambda: NumericRange(unit="g/L"))
    yan_mg_l: NumericRange = field(default_factory=lambda: NumericRange(unit="mg/L"))
    potassium_mg_l: NumericRange = field(default_factory=lambda: NumericRange(unit="mg/L"))
    anthocyanin_index: NumericRange = field(default_factory=NumericRange)
    tannin_index: NumericRange = field(default_factory=NumericRange)
    aroma_precursor_index: NumericRange = field(default_factory=NumericRange)


@dataclass
class SensoryProfile:
    acidity: float | None = None
    tannin: float | None = None
    body: float | None = None
    sweetness: float | None = None
    alcohol_pct: NumericRange = field(default_factory=lambda: NumericRange(unit="% abv"))
    fruit_intensity: float | None = None
    floral_intensity: float | None = None
    herbal_intensity: float | None = None
    earth_intensity: float | None = None
    spice_intensity: float | None = None
    oak_affinity: float | None = None
    primary_aromas: list[str] = field(default_factory=list)
    secondary_aromas: list[str] = field(default_factory=list)
    tertiary_aromas: list[str] = field(default_factory=list)


@dataclass
class GrapeKnowledge:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    color: str | None = None
    species: str | None = None
    origin_country: str | None = None
    origin_region: str | None = None
    parentage: list[str] = field(default_factory=list)
    mutations_or_clones: list[str] = field(default_factory=list)
    coverage: CoverageLevel = CoverageLevel.IDENTITY
    confidence: Confidence = Confidence.MEDIUM
    phenology: PhenologyProfile = field(default_factory=PhenologyProfile)
    viticulture: ViticultureProfile = field(default_factory=ViticultureProfile)
    must_chemistry: MustChemistryProfile = field(default_factory=MustChemistryProfile)
    sensory: SensoryProfile = field(default_factory=SensoryProfile)
    key_regions: list[str] = field(default_factory=list)
    blending_partners: list[str] = field(default_factory=list)
    aging_archetype: str | None = None
    source_ids: list[str] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)
    legacy_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class FruitHandling:
    hand_harvested: bool | None = None
    sorting_intensity: float | None = None
    destemmed_fraction: float | None = None
    whole_cluster_fraction: float | None = None
    crushed_fraction: float | None = None
    cold_soak_days: NumericRange = field(default_factory=lambda: NumericRange(unit="days"))
    pre_ferment_skin_contact_hours: NumericRange = field(default_factory=lambda: NumericRange(unit="hours"))
    must_settling_hours: NumericRange = field(default_factory=lambda: NumericRange(unit="hours"))
    inert_gas_protection: bool | None = None


@dataclass
class YeastProgram:
    mode: str | None = None                    # native, inoculated, mixed, pied-de-cuve
    strain_family: str | None = None
    pied_de_cuve: bool | None = None
    nutrient_strategy: str | None = None
    target_yan_mg_l: NumericRange = field(default_factory=lambda: NumericRange(unit="mg/L"))


@dataclass
class FermentationKinetics:
    vessel_material: str | None = None
    vessel_volume_l: NumericRange = field(default_factory=lambda: NumericRange(unit="L"))
    open_top: bool | None = None
    pressure_bar: NumericRange = field(default_factory=lambda: NumericRange(unit="bar"))
    start_temp_c: NumericRange = field(default_factory=lambda: NumericRange(unit="°C"))
    peak_temp_c: NumericRange = field(default_factory=lambda: NumericRange(unit="°C"))
    lag_hours: NumericRange = field(default_factory=lambda: NumericRange(unit="hours"))
    active_days: NumericRange = field(default_factory=lambda: NumericRange(unit="days"))
    total_days: NumericRange = field(default_factory=lambda: NumericRange(unit="days"))
    target_residual_sugar_g_l: NumericRange = field(default_factory=lambda: NumericRange(unit="g/L"))


@dataclass
class ExtractionProgram:
    maceration_days: NumericRange = field(default_factory=lambda: NumericRange(unit="days"))
    pumpovers_per_day: NumericRange = field(default_factory=lambda: NumericRange(unit="per day"))
    punchdowns_per_day: NumericRange = field(default_factory=lambda: NumericRange(unit="per day"))
    delestage_count: NumericRange = field(default_factory=NumericRange)
    carbonic_fraction: NumericRange = field(default_factory=lambda: NumericRange(unit="fraction"))
    intracellular_days: NumericRange = field(default_factory=lambda: NumericRange(unit="days"))
    submerged_cap: bool | None = None
    press_pressure_bar: NumericRange = field(default_factory=lambda: NumericRange(unit="bar"))
    free_run_fraction: NumericRange = field(default_factory=lambda: NumericRange(unit="fraction"))


@dataclass
class MalolacticProgram:
    enabled: bool | None = None
    mode: str | None = None                    # spontaneous, inoculated
    timing: str | None = None                  # co-inoculated, sequential, post-ferment
    temp_c: NumericRange = field(default_factory=lambda: NumericRange(unit="°C"))
    duration_days: NumericRange = field(default_factory=lambda: NumericRange(unit="days"))


@dataclass
class SulfurOxygenProgram:
    so2_at_crush_mg_l: NumericRange = field(default_factory=lambda: NumericRange(unit="mg/L"))
    so2_post_ferment_mg_l: NumericRange = field(default_factory=lambda: NumericRange(unit="mg/L"))
    free_so2_at_bottling_mg_l: NumericRange = field(default_factory=lambda: NumericRange(unit="mg/L"))
    dissolved_oxygen_at_bottling_mg_l: NumericRange = field(default_factory=lambda: NumericRange(unit="mg/L"))
    oxygen_exposure_index: float | None = None


@dataclass
class FaultRiskProfile:
    stuck_fermentation: float | None = None
    volatile_acidity: float | None = None
    hydrogen_sulfide: float | None = None
    reduction: float | None = None
    oxidation: float | None = None
    brettanomyces: float | None = None
    mousiness: float | None = None


@dataclass
class FermentationProgram:
    id: str
    name: str
    style_family: str
    fruit: FruitHandling = field(default_factory=FruitHandling)
    yeast: YeastProgram = field(default_factory=YeastProgram)
    kinetics: FermentationKinetics = field(default_factory=FermentationKinetics)
    extraction: ExtractionProgram = field(default_factory=ExtractionProgram)
    malolactic: MalolacticProgram = field(default_factory=MalolacticProgram)
    sulfur_oxygen: SulfurOxygenProgram = field(default_factory=SulfurOxygenProgram)
    fault_risk: FaultRiskProfile = field(default_factory=FaultRiskProfile)
    source_ids: list[str] = field(default_factory=list)
    is_simulation_prior: bool = True


@dataclass
class VesselProgram:
    material: str
    volume_l: NumericRange = field(default_factory=lambda: NumericRange(unit="L"))
    months: NumericRange = field(default_factory=lambda: NumericRange(unit="months"))
    new_oak_fraction: NumericRange = field(default_factory=lambda: NumericRange(unit="fraction"))
    oak_species: str | None = None
    oak_origin: str | None = None
    grain: str | None = None
    toast: str | None = None
    oxygen_transfer_index: float | None = None


@dataclass
class ElevageProgram:
    id: str
    name: str
    vessels: list[VesselProgram] = field(default_factory=list)
    total_months: NumericRange = field(default_factory=lambda: NumericRange(unit="months"))
    gross_lees_months: NumericRange = field(default_factory=lambda: NumericRange(unit="months"))
    fine_lees_months: NumericRange = field(default_factory=lambda: NumericRange(unit="months"))
    batonnage_per_month: NumericRange = field(default_factory=lambda: NumericRange(unit="per month"))
    racking_count: NumericRange = field(default_factory=NumericRange)
    topping_frequency_days: NumericRange = field(default_factory=lambda: NumericRange(unit="days"))
    micro_oxygenation: bool | None = None
    flor_aging: bool | None = None
    oxidative_handling: float | None = None
    fining: list[str] = field(default_factory=list)
    filtration_microns: NumericRange = field(default_factory=lambda: NumericRange(unit="µm"))
    cold_stabilized: bool | None = None
    closure: str | None = None
    closure_oxygen_transfer_index: float | None = None
    source_ids: list[str] = field(default_factory=list)
    is_simulation_prior: bool = True


@dataclass
class AgingArchetype:
    id: str
    name: str
    maturity_years: float
    peak_years: float
    decline_half_life_years: float
    primary_half_life_years: float
    floral_half_life_years: float
    tertiary_onset_years: float
    tertiary_peak_years: float
    tannin_softening_half_life_years: float
    freshness_half_life_years: float
    oxidation_onset_years: float
    oxidation_rate: float
    complexity_peak_years: float
    sediment_onset_years: float
    color_shift_rate: float
    bottle_variation: float = 0.05
    is_simulation_prior: bool = True


@dataclass
class AgingState:
    age_years: float
    primary_fruit: float
    floral: float
    tertiary: float
    tannin_structure: float
    freshness: float
    oxidation: float
    complexity: float
    sediment: float
    color_evolution: float
    condition: float


@dataclass
class SeasonalClimate:
    growing_degree_days: float | None = None
    mean_growing_temp_c: float | None = None
    temperature_anomaly_c: float | None = None
    rainfall_mm: float | None = None
    rainfall_anomaly_pct: float | None = None
    heatwave_days: int | None = None
    frost_events: int | None = None
    hail_events: int | None = None
    drought_index: float | None = None
    disease_pressure: float | None = None
    botrytis_pressure: float | None = None


@dataclass
class VintageKnowledge:
    id: str
    gi_id: str
    year: int
    climate: SeasonalClimate = field(default_factory=SeasonalClimate)
    yield_index: float | None = None
    harvest_timing_index: float | None = None
    ripeness_index: float | None = None
    acidity_retention_index: float | None = None
    tannin_quality_index: float | None = None
    heterogeneity_index: float | None = None
    early_accessibility: float | None = None
    longevity_modifier: float | None = None
    overall_quality: float | None = None
    red_quality: float | None = None
    white_quality: float | None = None
    sparkling_quality: float | None = None
    sweet_quality: float | None = None
    style_tags: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM


@dataclass
class GeographicIndication:
    id: str
    name: str
    country: str
    gi_type: str
    legal_status: str
    parent_id: str | None = None
    aliases: list[str] = field(default_factory=list)
    authority: str | None = None
    source_ids: list[str] = field(default_factory=list)
    established_date: str | None = None
    coverage: CoverageLevel = CoverageLevel.IDENTITY
    legacy_path: list[str] = field(default_factory=list)
