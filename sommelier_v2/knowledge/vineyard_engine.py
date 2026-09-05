"""Block-level vineyard mechanics with hard origin constraints.

Named sites are physical/administrative places. Appellation eligibility is evaluated
separately. A grower may experimentally plant a grape in a place, but the engine
will not silently label the resulting wine with a protected origin when the grape
is not permitted or when the legal rule is unknown.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import cos, radians
from typing import Iterable

from .expanded_catalog import NamedSite, WorldWineKnowledgeCatalog
from .regional_rules import OriginConstraintError, OriginDecision, RegionGrapeRulebook
from .vintage_engine import DailyWeather, VintageModelParams, VintageOutcome, clamp, simulate_vintage


@dataclass(frozen=True)
class VineyardBlock:
    id: str
    grape: str
    area_ha: float
    planting_year: int
    country: str
    region: str
    appellation: str | None = None
    site_id: str | None = None
    producer: str | None = None
    label_scope: str = "country_wine"
    experimental: bool = False

    elevation_m: float = 250.0
    slope_pct: float = 5.0
    aspect_degrees: float = 180.0
    row_orientation_degrees: float = 0.0
    vine_density_per_ha: int = 4500
    target_yield_t_ha: float = 7.0
    crop_load_index: float = 1.0
    soil_water_capacity_mm: float = 140.0
    initial_soil_water_mm: float = 100.0
    temperature_offset_c: float = 0.0
    rainfall_multiplier: float = 1.0
    solar_multiplier: float = 1.0
    wind_multiplier: float = 1.0

    irrigation_mm_per_week: float = 0.0
    irrigation_allowed: bool = True
    canopy_management_index: float = 0.6
    disease_control_index: float = 0.6
    organic: bool = False
    biodynamic: bool = False
    rootstock: str | None = None
    training_system: str | None = None


@dataclass(frozen=True)
class VineyardOutcome:
    block_id: str
    grape: str
    site_id: str | None
    origin_decision: OriginDecision
    vintage: VintageOutcome
    harvestable: bool
    failed_to_ripen: bool
    label_eligible: bool
    site_claim_eligible: bool
    yield_t_ha: float
    yield_hl_ha: float
    total_grape_tonnes: float
    brix: float
    potential_alcohol_pct: float
    ph: float
    titratable_acidity_g_l: float
    malic_acid_g_l: float
    berry_size_index: float
    disease_loss_fraction: float
    rot_loss_fraction: float
    vine_age_years: int
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class SiteRegistry:
    def __init__(self, sites: Iterable[NamedSite]) -> None:
        self.sites = list(sites)
        self.by_id = {site.id: site for site in self.sites}
        self.by_name: dict[tuple[str, str, str], list[NamedSite]] = {}
        for site in self.sites:
            key = (_norm(site.country), _norm(site.region), _norm(site.name))
            self.by_name.setdefault(key, []).append(site)

    def resolve(
        self,
        *,
        site_id: str | None = None,
        country: str | None = None,
        region: str | None = None,
        name: str | None = None,
        parent: str | None = None,
    ) -> NamedSite | None:
        if site_id:
            return self.by_id.get(site_id)
        if not (country and region and name):
            return None
        rows = list(self.by_name.get((_norm(country), _norm(region), _norm(name)), []))
        if parent:
            parent_key = _norm(parent)
            rows = [row for row in rows if _norm(row.parent) == parent_key]
        return rows[0] if len(rows) == 1 else None

    def validate_ownership(self, site: NamedSite, producer: str | None) -> None:
        if site.site_type not in {"monopole", "block"}:
            return
        if site.owner and _norm(site.owner) != _norm(producer):
            raise OriginConstraintError(
                f"{site.name} is recorded as a {site.site_type} controlled by {site.owner}; producer {producer or '<unspecified>'} cannot claim it."
            )


def _norm(value: str | None) -> str:
    from .catalog import normalize_name
    return normalize_name(value or "")


def _bounded(value: float | None, default: float = 0.5) -> float:
    return clamp(default if value is None else float(value))


class VineyardEngine:
    def __init__(
        self,
        *,
        catalog: WorldWineKnowledgeCatalog | None = None,
        rulebook: RegionGrapeRulebook | None = None,
        sites: Iterable[NamedSite] | None = None,
    ) -> None:
        self.catalog = catalog or WorldWineKnowledgeCatalog()
        self.rulebook = rulebook or RegionGrapeRulebook(catalog=self.catalog)
        self.site_registry = SiteRegistry(sites if sites is not None else self.catalog.named_sites)

    def validate_block(self, block: VineyardBlock, *, vintage_year: int) -> tuple[NamedSite | None, OriginDecision]:
        issues: list[str] = []
        if not block.id.strip():
            issues.append("Block ID is required")
        if block.area_ha <= 0 or block.area_ha > 10000:
            issues.append("Block area must be >0 and <=10,000 ha")
        if block.planting_year < 1800 or block.planting_year > vintage_year:
            issues.append("Planting year must be between 1800 and the vintage year")
        if block.vine_density_per_ha < 100 or block.vine_density_per_ha > 30000:
            issues.append("Vine density is outside the supported physical range 100..30,000 vines/ha")
        if block.target_yield_t_ha <= 0 or block.target_yield_t_ha > 60:
            issues.append("Target yield is outside the supported range 0..60 t/ha")
        if block.soil_water_capacity_mm <= 10 or block.soil_water_capacity_mm > 600:
            issues.append("Soil water capacity must be within 10..600 mm")
        if not 0 <= block.irrigation_mm_per_week <= 200:
            issues.append("Irrigation must be within 0..200 mm/week")
        if block.irrigation_mm_per_week > 0 and not block.irrigation_allowed:
            issues.append("Irrigation is configured for a block marked irrigation-disallowed")
        if not 0.2 <= block.rainfall_multiplier <= 3.0:
            issues.append("Rainfall multiplier must be within 0.2..3.0")
        if not 0.4 <= block.solar_multiplier <= 1.8:
            issues.append("Solar multiplier must be within 0.4..1.8")
        if not 0.2 <= block.wind_multiplier <= 4.0:
            issues.append("Wind multiplier must be within 0.2..4.0")
        if issues:
            raise ValueError("; ".join(issues))

        site = self.site_registry.resolve(site_id=block.site_id) if block.site_id else None
        if block.site_id and site is None:
            raise OriginConstraintError(f"Unknown named vineyard/site ID: {block.site_id}")
        if site is not None:
            if _norm(site.country) != _norm(block.country):
                raise OriginConstraintError(f"Site {site.name} is in {site.country}, not {block.country}")
            if _norm(site.region) != _norm(block.region):
                raise OriginConstraintError(f"Site {site.name} belongs to {site.region}, not {block.region}")
            self.site_registry.validate_ownership(site, block.producer)

        appellation = block.appellation
        if appellation is None and site is not None:
            appellation = site.parent or site.region

        decision = self.rulebook.evaluate(
            country=block.country,
            region=block.region,
            appellation=appellation,
            grapes={block.grape: 100.0},
            label_scope=block.label_scope,
            vintage_year=vintage_year,
            experimental=block.experimental,
        )
        if not decision.eligible and block.label_scope.casefold() == "regulated_gi":
            decision.require()
        return site, decision

    def _params_for(self, block: VineyardBlock) -> VintageModelParams:
        grape = self.catalog.grape(block.grape)
        phen = grape.phenology if grape is not None else None
        vit = grape.viticulture if grape is not None else None

        heat = _bounded(getattr(phen, "heat_requirement_index", None), 0.5)
        bud_rel = float(getattr(phen, "budbreak_relative", 0.0) or 0.0)
        flower_rel = float(getattr(phen, "flowering_relative", 0.0) or 0.0)
        veraison_rel = float(getattr(phen, "veraison_relative", 0.0) or 0.0)
        harvest_rel = float(getattr(phen, "harvest_relative", 0.0) or 0.0)

        target = 1125.0 + 575.0 * heat + 90.0 * harvest_rel
        return VintageModelParams(
            budbreak_gdd=max(40.0, 80.0 + 22.0 * bud_rel),
            flowering_gdd=max(220.0, 350.0 + 55.0 * flower_rel),
            veraison_gdd=max(650.0, 875.0 + 90.0 * veraison_rel),
            target_harvest_gdd=max(900.0, target),
            max_harvest_gdd=max(1150.0, target + 300.0),
            field_capacity_mm=block.soil_water_capacity_mm,
            initial_soil_water_mm=min(block.initial_soil_water_mm, block.soil_water_capacity_mm),
            variety_acidity_retention=_bounded(getattr(vit, "acidity_retention", None), 0.5),
            variety_drought_tolerance=_bounded(getattr(vit, "drought_tolerance", None), 0.5),
            variety_heat_sensitivity=_bounded(getattr(phen, "heat_spike_sensitivity", None), 0.5),
            variety_botrytis_susceptibility=_bounded(getattr(vit, "botrytis_susceptibility", None), 0.5),
            variety_rot_susceptibility=_bounded(getattr(vit, "rot_susceptibility", None), 0.5),
        )

    def _microclimate(self, block: VineyardBlock, days: list[DailyWeather]) -> list[DailyWeather]:
        if not days:
            raise ValueError("weather_days must not be empty")
        canopy = clamp(block.canopy_management_index)
        disease_control = clamp(block.disease_control_index)
        warm_aspect = 180.0 if block.country not in {
            "Australia", "New Zealand", "South Africa", "Chile", "Argentina", "Uruguay"
        } else 0.0
        aspect_delta = cos(radians(block.aspect_degrees - warm_aspect))
        aspect_temp = 0.55 * aspect_delta * clamp(block.slope_pct / 35.0)
        altitude_cooling = -0.0065 * (block.elevation_m - 250.0)
        temp_offset = block.temperature_offset_c + aspect_temp + altitude_cooling
        irrigation_daily = block.irrigation_mm_per_week / 7.0 if block.irrigation_allowed else 0.0

        adjusted: list[DailyWeather] = []
        for weather in days:
            humidity = clamp((weather.humidity_pct - 10.0 * canopy - 8.0 * disease_control) / 100.0, 0.15, 1.0) * 100.0
            adjusted.append(
                replace(
                    weather,
                    tmin_c=weather.tmin_c + temp_offset,
                    tmax_c=weather.tmax_c + temp_offset,
                    rain_mm=max(0.0, weather.rain_mm * block.rainfall_multiplier + irrigation_daily),
                    humidity_pct=humidity,
                    solar_mj_m2=max(0.0, weather.solar_mj_m2 * block.solar_multiplier),
                    wind_m_s=max(0.0, weather.wind_m_s * block.wind_multiplier),
                )
            )
        return adjusted

    def simulate(self, block: VineyardBlock, weather_days: list[DailyWeather], *, vintage_year: int) -> VineyardOutcome:
        site, origin = self.validate_block(block, vintage_year=vintage_year)
        params = self._params_for(block)
        vintage = simulate_vintage(self._microclimate(block, weather_days), params)

        age = max(0, vintage_year - block.planting_year)
        maturity = clamp(age / 8.0)
        senescence = clamp((age - 70.0) / 50.0)
        crop_load = clamp(block.crop_load_index, 0.2, 1.8)

        disease_loss = clamp(0.24 * vintage.disease_pressure + 0.32 * vintage.botrytis_pressure - 0.18 * clamp(block.disease_control_index))
        rot_loss = clamp(0.42 * vintage.botrytis_pressure + 0.18 * vintage.harvest_window_rain_mm / 120.0 - 0.15 * clamp(block.canopy_management_index))

        yield_t_ha = block.target_yield_t_ha * vintage.yield_index * (0.72 + 0.28 * maturity) * (1.0 - 0.22 * senescence) * crop_load * (1.0 - disease_loss) * (1.0 - rot_loss)
        yield_t_ha = max(0.0, min(60.0, yield_t_ha))
        yield_hl_ha = yield_t_ha * 7.0

        brix = max(12.0, min(32.0, 16.0 + 10.5 * vintage.ripeness_index + 1.0 * vintage.concentration_index - 1.2 * (crop_load - 1.0)))
        potential_alcohol = brix * 0.59
        acid_retention = vintage.acidity_retention_index
        ph = max(2.65, min(4.25, 3.65 - 0.72 * acid_retention + 0.16 * vintage.drought_stress + 0.10 * clamp(vintage.hot_nights / 20.0)))
        ta = max(3.0, min(13.0, 4.2 + 6.8 * acid_retention - 1.0 * vintage.ripeness_index + 0.6 * clamp(vintage.harvest_window_rain_mm / 100.0)))
        malic = max(0.2, min(7.0, 0.55 + 5.3 * acid_retention - 1.8 * clamp(vintage.hot_nights / 20.0)))
        berry_size = clamp(0.45 + 0.40 * (1.0 - vintage.drought_stress) + 0.12 * clamp(vintage.growing_season_rain_mm / 550.0))

        failed_to_ripen = vintage.ripeness_index < 0.50 or brix < 17.0 or vintage.growing_degree_days < params.target_harvest_gdd * 0.78
        harvestable = not failed_to_ripen and rot_loss < 0.72 and disease_loss < 0.72 and yield_t_ha > 0.05

        issues = list(origin.issues)
        warnings = list(origin.warnings)
        label_eligible = origin.eligible and harvestable

        rule = self.rulebook.resolve(
            country=block.country,
            region=block.region,
            appellation=block.appellation or (site.parent if site else None),
        )
        if block.label_scope.casefold() == "regulated_gi" and rule is not None:
            if rule.max_yield_hl_ha and yield_hl_ha > rule.max_yield_hl_ha:
                label_eligible = False
                issues.append(f"Yield {yield_hl_ha:.1f} hL/ha exceeds {rule.max_yield_hl_ha:.1f} hL/ha for the resolved origin.")
            if rule.min_alcohol_pct and potential_alcohol < rule.min_alcohol_pct:
                label_eligible = False
                issues.append(f"Potential alcohol {potential_alcohol:.1f}% is below the origin minimum {rule.min_alcohol_pct:.1f}%.")

        if failed_to_ripen:
            issues.append("The block did not reach minimum ripeness for a normal commercial harvest.")
        if not harvestable and not failed_to_ripen:
            issues.append("Disease, rot, or crop failure made the block non-harvestable.")

        site_claim_eligible = bool(site) and label_eligible
        if site is not None and site.site_type == "block" and not site.owner:
            site_claim_eligible = False
            warnings.append("Producer block lacks an owner binding; site name cannot be auto-claimed.")

        return VineyardOutcome(
            block_id=block.id,
            grape=origin.canonical_grapes[0] if origin.canonical_grapes else block.grape,
            site_id=site.id if site else None,
            origin_decision=origin,
            vintage=vintage,
            harvestable=harvestable,
            failed_to_ripen=failed_to_ripen,
            label_eligible=label_eligible,
            site_claim_eligible=site_claim_eligible,
            yield_t_ha=yield_t_ha,
            yield_hl_ha=yield_hl_ha,
            total_grape_tonnes=yield_t_ha * block.area_ha,
            brix=brix,
            potential_alcohol_pct=potential_alcohol,
            ph=ph,
            titratable_acidity_g_l=ta,
            malic_acid_g_l=malic,
            berry_size_index=berry_size,
            disease_loss_fraction=disease_loss,
            rot_loss_fraction=rot_loss,
            vine_age_years=age,
            issues=tuple(issues),
            warnings=tuple(warnings),
        )
