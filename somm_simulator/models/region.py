"""Wine region hierarchy model."""

from __future__ import annotations
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class Commune:
    """Smallest wine geographic unit (village/commune/AVA)."""
    name: str
    classification_system: str = ""
    classification_tiers: list[str] = field(default_factory=list)
    primary_grapes: list[str] = field(default_factory=list)
    soil_types: list[str] = field(default_factory=list)
    style_notes: str = ""
    price_tier: str = "moderate"  # value, moderate, premium, luxury, ultra_luxury
    climate: str = "continental"
    # Legal and production constraints
    allowed_grapes: list[str] = field(default_factory=list)   # Legally permitted grapes (empty = unrestricted)
    max_yield_hl_ha: float = 0.0       # Legal max yield in hl/ha (0 = unregulated)
    min_alcohol: float = 0.0           # Minimum alcohol by law
    required_aging_months: int = 0     # Minimum aging before release
    # Viticultural characteristics
    elevation_m: tuple[int, int] = (0, 0)  # Elevation range in meters
    annual_rainfall_mm: int = 0
    growing_degree_days: int = 0       # Heat accumulation (Winkler-style)
    phylloxera_free: bool = False      # Region never had phylloxera (e.g., Chile, parts of Australia)
    ungrafted_vines_common: bool = False  # Sandy/volcanic soils allow own-root vines
    organic_percentage: float = 0.0    # Approximate % of vineyards certified organic
    biodynamic_percentage: float = 0.0
    natural_wine_hub: bool = False     # Known center of natural wine production


@dataclass
class SubRegion:
    """Sub-region containing communes."""
    name: str
    communes: list[Commune] = field(default_factory=list)
    primary_grapes: list[str] = field(default_factory=list)
    climate: str = "continental"
    style_notes: str = ""


@dataclass
class WineRegion:
    """Major wine region within a country."""
    name: str
    sub_regions: list[SubRegion] = field(default_factory=list)
    classification_system: str = ""
    primary_grapes: list[str] = field(default_factory=list)
    climate: str = "continental"
    style_notes: str = ""


@dataclass
class Country:
    """Country with its wine regions."""
    country: str
    wine_regions: list[WineRegion] = field(default_factory=list)


class RegionDatabase:
    """Loads and queries the region hierarchy."""

    def __init__(self, data_path: Path | None = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent / "data" / "regions.json"
        self.countries: list[Country] = []
        self._load(data_path)

    def _load(self, path: Path):
        with open(path, "r") as f:
            data = json.load(f)
        for country_data in data.get("regions", []):
            country = Country(country=country_data["country"])
            for wr_data in country_data.get("wine_regions", []):
                wine_region = WineRegion(
                    name=wr_data["name"],
                    classification_system=wr_data.get("classification_system", ""),
                    primary_grapes=wr_data.get("primary_grapes", []),
                    climate=wr_data.get("climate", "continental"),
                    style_notes=wr_data.get("style_notes", ""),
                )
                for sr_data in wr_data.get("sub_regions", []):
                    sub_region = SubRegion(
                        name=sr_data["name"],
                        primary_grapes=sr_data.get("primary_grapes", []),
                        climate=sr_data.get("climate", wine_region.climate),
                        style_notes=sr_data.get("style_notes", ""),
                    )
                    for c_data in sr_data.get("communes", []):
                        elev = c_data.get("elevation_m", [0, 0])
                        commune = Commune(
                            name=c_data["name"],
                            classification_system=c_data.get("classification_system", ""),
                            classification_tiers=c_data.get("classification_tiers", []),
                            primary_grapes=c_data.get("primary_grapes", sub_region.primary_grapes),
                            soil_types=c_data.get("soil_types", []),
                            style_notes=c_data.get("style_notes", ""),
                            price_tier=c_data.get("price_tier", "moderate"),
                            climate=c_data.get("climate", sub_region.climate),
                            allowed_grapes=c_data.get("allowed_grapes", []),
                            max_yield_hl_ha=c_data.get("max_yield_hl_ha", 0.0),
                            min_alcohol=c_data.get("min_alcohol", 0.0),
                            required_aging_months=c_data.get("required_aging_months", 0),
                            elevation_m=(elev[0], elev[1]) if isinstance(elev, list) and len(elev) == 2 else (0, 0),
                            annual_rainfall_mm=c_data.get("annual_rainfall_mm", 0),
                            growing_degree_days=c_data.get("growing_degree_days", 0),
                            phylloxera_free=c_data.get("phylloxera_free", False),
                            ungrafted_vines_common=c_data.get("ungrafted_vines_common", False),
                            organic_percentage=c_data.get("organic_percentage", 0.0),
                            biodynamic_percentage=c_data.get("biodynamic_percentage", 0.0),
                            natural_wine_hub=c_data.get("natural_wine_hub", False),
                        )
                        sub_region.communes.append(commune)
                    wine_region.sub_regions.append(sub_region)
                country.wine_regions.append(wine_region)
            self.countries.append(country)

    def all_communes(self) -> list[tuple[str, str, str, Commune]]:
        """Return all communes as (country, region, sub_region, commune) tuples."""
        results = []
        for country in self.countries:
            for region in country.wine_regions:
                for sub_region in region.sub_regions:
                    for commune in sub_region.communes:
                        results.append((
                            country.country,
                            region.name,
                            sub_region.name,
                            commune,
                        ))
        return results

    def get_country(self, name: str) -> Country | None:
        for c in self.countries:
            if c.country.lower() == name.lower():
                return c
        return None

    def get_region(self, country: str, region: str) -> WineRegion | None:
        c = self.get_country(country)
        if c:
            for r in c.wine_regions:
                if r.name.lower() == region.lower():
                    return r
        return None

    def country_names(self) -> list[str]:
        return [c.country for c in self.countries]

    def region_names(self, country: str) -> list[str]:
        c = self.get_country(country)
        return [r.name for r in c.wine_regions] if c else []
