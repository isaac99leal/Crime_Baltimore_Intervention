"""Couple vineyard harvest outcomes to cellar must composition.

The vineyard and fermentation engines intentionally remain separate. This module
is the explicit boundary between them. It transfers modeled harvest chemistry,
models processing losses, and refuses to invent laboratory measurements that the
vineyard model cannot support.

All coefficients that convert harvest condition into sorting loss or risk scores
are simulation priors. They are not laboratory prediction equations. Measured
YAN is preferred; when it is unavailable, callers must explicitly provide a
fallback YAN prior rather than receiving a silent estimate.
"""
from __future__ import annotations

from dataclasses import dataclass

from .fermentation_engine import AlcoholicFermentationParams
from .fermentation_process import MustComposition
from .vineyard_engine import VineyardOutcome
from .vintage_engine import clamp


class HarvestMustConstraintError(ValueError):
    """Raised when a harvest cannot be converted into a defensible must state."""


@dataclass(frozen=True)
class HarvestMustPlan:
    """Physical processing choices used to turn harvested fruit into must.

    ``juice_yield_l_per_tonne`` is a configurable process prior because press
    yield varies with variety, berry condition, equipment, press cycle, and the
    inclusion or exclusion of press fractions.
    """

    style: str = "red"
    juice_yield_l_per_tonne: float = 700.0
    sorting_intensity: float = 0.60
    clarification_loss_fraction: float = 0.02
    must_temp_c: float = 18.0
    free_so2_mg_l: float = 5.0
    solids_pct: float | None = None
    measured_yan_mg_l: float | None = None
    fallback_yan_mg_l: float | None = None
    initial_biomass_g_l: float = 0.12
    initial_ethanol_pct: float = 0.0
    allow_compromised_harvest: bool = False


@dataclass(frozen=True)
class HarvestMustProfile:
    """Must plus the physical and uncertainty state that produced it."""

    must: MustComposition
    source_block_id: str
    source_grape: str
    harvested_tonnes: float
    sorting_loss_fraction: float
    usable_tonnes: float
    must_volume_l: float
    yan_source: str
    retained_botrytis_fraction: float
    retained_rot_fraction: float
    fruit_integrity_index: float
    microbial_risk_index: float
    oxidation_risk_index: float
    extraction_potential_index: float
    warnings: tuple[str, ...] = ()


def _bounded(name: str, value: float, low: float, high: float) -> None:
    if not low <= value <= high:
        raise HarvestMustConstraintError(
            f"{name} must be within {low}..{high}; got {value}"
        )


def _default_solids(style: str) -> float:
    key = style.strip().casefold()
    if key in {"white", "rosé", "rose", "sparkling_base"}:
        return 2.0
    if key == "orange":
        return 10.0
    if key == "red":
        return 12.0
    raise HarvestMustConstraintError(f"Unsupported harvest-to-must style {style!r}")


def validate_harvest_must_plan(plan: HarvestMustPlan) -> None:
    _bounded("juice_yield_l_per_tonne", plan.juice_yield_l_per_tonne, 100.0, 1000.0)
    _bounded("sorting_intensity", plan.sorting_intensity, 0.0, 1.0)
    _bounded("clarification_loss_fraction", plan.clarification_loss_fraction, 0.0, 0.50)
    _bounded("must_temp_c", plan.must_temp_c, -5.0, 45.0)
    _bounded("free_so2_mg_l", plan.free_so2_mg_l, 0.0, 300.0)
    _bounded("initial_biomass_g_l", plan.initial_biomass_g_l, 0.001, 20.0)
    _bounded("initial_ethanol_pct", plan.initial_ethanol_pct, 0.0, 25.0)
    if plan.solids_pct is not None:
        _bounded("solids_pct", plan.solids_pct, 0.0, 60.0)
    if plan.measured_yan_mg_l is not None:
        _bounded("measured_yan_mg_l", plan.measured_yan_mg_l, 0.0, 1200.0)
    if plan.fallback_yan_mg_l is not None:
        _bounded("fallback_yan_mg_l", plan.fallback_yan_mg_l, 0.0, 1200.0)
    _default_solids(plan.style)


def _yan(plan: HarvestMustPlan) -> tuple[float, str, list[str]]:
    warnings: list[str] = []
    if plan.measured_yan_mg_l is not None:
        return plan.measured_yan_mg_l, "measured", warnings
    if plan.fallback_yan_mg_l is not None:
        warnings.append(
            "YAN is an explicit caller-supplied prior, not a measured harvest value."
        )
        return plan.fallback_yan_mg_l, "explicit_prior", warnings
    raise HarvestMustConstraintError(
        "YAN cannot be inferred defensibly from the vineyard outcome. Supply "
        "measured_yan_mg_l or an explicit fallback_yan_mg_l prior."
    )


def _retained_condition(
    outcome: VineyardOutcome,
    sorting_intensity: float,
) -> tuple[float, float, float]:
    """Return retained botrytis, retained rot, and sorting mass loss priors.

    Vineyard losses are crop-level losses, not a direct assay of fruit entering
    the crusher. We therefore use vintage disease pressure and the crop-loss
    indicators only as bounded proxies, then make sorting an explicit cellar
    intervention.
    """
    raw_botrytis = clamp(
        0.55 * outcome.vintage.botrytis_pressure
        + 0.15 * outcome.disease_loss_fraction
    )
    raw_rot = clamp(
        0.45 * outcome.rot_loss_fraction
        + 0.20 * outcome.vintage.disease_pressure
    )
    retained_botrytis = clamp(raw_botrytis * (1.0 - 0.82 * sorting_intensity))
    retained_rot = clamp(raw_rot * (1.0 - 0.90 * sorting_intensity))
    sorting_loss = clamp(
        sorting_intensity * (0.32 * raw_botrytis + 0.58 * raw_rot),
        0.0,
        0.45,
    )
    return retained_botrytis, retained_rot, sorting_loss


def must_from_vineyard(
    outcome: VineyardOutcome,
    plan: HarvestMustPlan = HarvestMustPlan(),
    *,
    alcoholic_params: AlcoholicFermentationParams = AlcoholicFermentationParams(),
) -> HarvestMustProfile:
    """Build a fermentation-ready must from one vineyard outcome.

    Sugar is derived from the vineyard model's potential-alcohol output using
    the same sugar-to-ABV conversion configured in the fermentation engine. This
    preserves mass-model consistency instead of applying a second independent
    Brix conversion.
    """
    validate_harvest_must_plan(plan)
    warnings: list[str] = []

    if outcome.total_grape_tonnes <= 0.0:
        raise HarvestMustConstraintError("Harvest has no grape mass to process.")
    if not outcome.harvestable and not plan.allow_compromised_harvest:
        raise HarvestMustConstraintError(
            "Vineyard outcome is non-harvestable; set allow_compromised_harvest=True "
            "only when the simulation intentionally processes compromised fruit."
        )
    if not outcome.harvestable:
        warnings.append("Compromised/non-commercial harvest was forced into cellar processing.")
    if not outcome.label_eligible:
        warnings.append(
            "The physical fruit can be processed, but the vineyard outcome is not "
            "eligible for its requested protected-origin label."
        )

    yan, yan_source, yan_warnings = _yan(plan)
    warnings.extend(yan_warnings)

    botrytis, rot, sorting_loss = _retained_condition(outcome, plan.sorting_intensity)
    usable_tonnes = outcome.total_grape_tonnes * (1.0 - sorting_loss)
    gross_must_l = usable_tonnes * plan.juice_yield_l_per_tonne
    must_volume_l = gross_must_l * (1.0 - plan.clarification_loss_fraction)
    if must_volume_l <= 0.0:
        raise HarvestMustConstraintError("Processing choices leave no must volume.")

    sugar_g_l = max(
        0.0,
        outcome.potential_alcohol_pct * alcoholic_params.sugar_g_l_per_abv_pct,
    )
    solids = plan.solids_pct if plan.solids_pct is not None else _default_solids(plan.style)

    heterogeneity = clamp(outcome.vintage.heterogeneity_index)
    heat_damage = clamp(outcome.vintage.extreme_heat_days / 12.0)
    wet_harvest = clamp(outcome.vintage.harvest_window_rain_mm / 120.0)
    fruit_integrity = clamp(
        1.0
        - 0.42 * rot
        - 0.28 * botrytis
        - 0.14 * heterogeneity
        - 0.10 * heat_damage
    )
    warm_intake = clamp((plan.must_temp_c - 20.0) / 15.0)
    microbial_risk = clamp(
        0.46 * rot
        + 0.34 * botrytis
        + 0.12 * wet_harvest
        + 0.08 * warm_intake
    )
    sulfur_protection = clamp(plan.free_so2_mg_l / 40.0)
    oxidation_risk = clamp(
        0.34 * rot
        + 0.20 * botrytis
        + 0.18 * heterogeneity
        + 0.12 * heat_damage
        + 0.16 * (1.0 - sulfur_protection)
    )
    skin_contact = 0.25 if plan.style.casefold() in {"white", "rosé", "rose", "sparkling_base"} else 1.0
    extraction_potential = clamp(
        skin_contact
        * (0.42 * outcome.vintage.concentration_index
           + 0.38 * outcome.vintage.tannin_quality_index
           + 0.20 * outcome.vintage.phenolic_ripeness_index)
        * (1.0 - 0.35 * rot)
    )

    must = MustComposition(
        volume_l=must_volume_l,
        sugar_g_l=sugar_g_l,
        yan_mg_l=yan,
        ph=outcome.ph,
        titratable_acidity_g_l=outcome.titratable_acidity_g_l,
        malic_acid_g_l=outcome.malic_acid_g_l,
        temp_c=plan.must_temp_c,
        initial_ethanol_pct=plan.initial_ethanol_pct,
        initial_biomass_g_l=plan.initial_biomass_g_l,
        free_so2_mg_l=plan.free_so2_mg_l,
        solids_pct=solids,
        botrytis_fraction=botrytis,
        rot_fraction=rot,
    )

    if microbial_risk >= 0.60:
        warnings.append("Harvest condition creates elevated modeled microbial risk at crush.")
    if oxidation_risk >= 0.60:
        warnings.append("Harvest condition creates elevated modeled oxidation risk at crush.")
    if sorting_loss >= 0.20:
        warnings.append("Sorting removes at least 20% of modeled harvested fruit mass.")

    return HarvestMustProfile(
        must=must,
        source_block_id=outcome.block_id,
        source_grape=outcome.grape,
        harvested_tonnes=outcome.total_grape_tonnes,
        sorting_loss_fraction=sorting_loss,
        usable_tonnes=usable_tonnes,
        must_volume_l=must_volume_l,
        yan_source=yan_source,
        retained_botrytis_fraction=botrytis,
        retained_rot_fraction=rot,
        fruit_integrity_index=fruit_integrity,
        microbial_risk_index=microbial_risk,
        oxidation_risk_index=oxidation_risk,
        extraction_potential_index=extraction_potential,
        warnings=tuple(warnings),
    )
