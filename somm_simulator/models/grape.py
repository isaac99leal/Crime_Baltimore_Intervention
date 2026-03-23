"""Grape variety data model."""

from __future__ import annotations
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class GrapeVariety:
    """A grape variety with its typical characteristics."""
    name: str
    color: str                    # "red", "white", or "grey"
    origin_country: str = ""
    origin_region: str = ""
    aliases: list[str] = field(default_factory=list)
    # Typical tasting profile (1-5 scale except alcohol)
    acidity: float = 3.0
    tannin: float = 3.0
    body: float = 3.0
    sweetness: float = 1.0
    alcohol_low: float = 12.0
    alcohol_high: float = 14.0
    fruit_intensity: float = 3.0
    earth_intensity: float = 2.0
    oak_affinity: float = 2.0    # How well it takes to oak aging
    primary_aromas: list[str] = field(default_factory=list)
    secondary_aromas: list[str] = field(default_factory=list)
    tertiary_aromas: list[str] = field(default_factory=list)
    color_descriptors: list[str] = field(default_factory=list)
    key_regions: list[str] = field(default_factory=list)
    aging_potential: str = "moderate"  # low, moderate, high, exceptional
    blending_partners: list[str] = field(default_factory=list)
    food_affinities: list[str] = field(default_factory=list)
    difficulty_to_identify: int = 3  # 1=easy, 5=very hard
    fun_fact: str = ""
    # Viticultural attributes
    climate_preferences: list[str] = field(default_factory=list)  # cool, moderate, warm, hot, continental, maritime, mediterranean
    vigor: str = "moderate"           # low, moderate, high
    yield_potential: str = "moderate"  # low, moderate, high
    disease_resistance: str = "moderate"  # low, moderate, high
    drought_tolerance: str = "moderate"  # low, moderate, high
    frost_resistance: str = "moderate"   # low, moderate, high
    phylloxera_resistant: bool = False   # True for some American/hybrid varieties
    can_grow_ungrafted: bool = False     # True in sandy/volcanic soils or phylloxera-free areas
    typical_rootstocks: list[str] = field(default_factory=list)
    # Winemaking attributes
    oxidative_style_suitable: bool = False  # Suitable for oxidative/amber/orange wine
    skin_contact_suitable: bool = False     # Suitable for extended skin contact (orange wine)
    sparkling_suitable: bool = False        # Suitable for sparkling wine production
    fortified_suitable: bool = False        # Suitable for fortified wine production
    late_harvest_suitable: bool = False     # Suitable for late harvest / botrytis
    carbonic_maceration: bool = False       # Suitable for carbonic maceration (Beaujolais style)
    # Production method affinities (how well the grape responds to these methods)
    organic_suitability: str = "moderate"   # low, moderate, high
    biodynamic_affinity: str = "moderate"   # low, moderate, high
    natural_wine_suitable: bool = False     # Makes good natural wine (low intervention)
    amphora_suitable: bool = False          # Suitable for amphora/qvevri aging
    # Classification
    is_indigenous: bool = False    # Native to a specific small area
    is_international: bool = False  # Widely planted globally
    is_hybrid: bool = False        # Vitis vinifera cross with other species
    is_table_grape: bool = False   # Also used as table grape
    endangered: bool = False       # Rare/nearly extinct variety


class GrapeDatabase:
    """Loads and queries grape variety data."""

    def __init__(self, data_path: Path | None = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent / "data" / "grapes.json"
        self.varieties: list[GrapeVariety] = []
        self._by_name: dict[str, GrapeVariety] = {}
        self._load(data_path)

    def _load(self, path: Path):
        with open(path, "r") as f:
            data = json.load(f)
        for g in data.get("grapes", []):
            profile = g.get("typical_profile", {})
            vit = g.get("viticulture", {})
            wm = g.get("winemaking", {})
            variety = GrapeVariety(
                name=g["name"],
                color=g["color"],
                origin_country=g.get("origin_country", ""),
                origin_region=g.get("origin_region", ""),
                aliases=g.get("aliases", []),
                acidity=profile.get("acidity", 3.0),
                tannin=profile.get("tannin", 3.0),
                body=profile.get("body", 3.0),
                sweetness=profile.get("sweetness", 1.0),
                alcohol_low=profile.get("alcohol_range", {"low": 12.0})["low"] if isinstance(profile.get("alcohol_range"), dict) else profile.get("alcohol_range", [12.0, 14.0])[0],
                alcohol_high=profile.get("alcohol_range", {"high": 14.0})["high"] if isinstance(profile.get("alcohol_range"), dict) else profile.get("alcohol_range", [12.0, 14.0])[1],
                fruit_intensity=profile.get("fruit_intensity", 3.0),
                earth_intensity=profile.get("earth_intensity", 2.0),
                oak_affinity=profile.get("oak_affinity", 2.0),
                primary_aromas=g.get("primary_aromas", []),
                secondary_aromas=g.get("secondary_aromas", []),
                tertiary_aromas=g.get("tertiary_aromas", []),
                color_descriptors=g.get("color_descriptors", []),
                key_regions=g.get("key_regions", []),
                aging_potential=g.get("aging_potential", "moderate"),
                blending_partners=g.get("blending_partners", []),
                food_affinities=g.get("food_affinities", []),
                difficulty_to_identify=g.get("difficulty_to_identify", 3),
                fun_fact=g.get("fun_fact", ""),
                # Viticultural attributes
                climate_preferences=vit.get("climate_preferences", []),
                vigor=vit.get("vigor", "moderate"),
                yield_potential=vit.get("yield_potential", "moderate"),
                disease_resistance=vit.get("disease_resistance", "moderate"),
                drought_tolerance=vit.get("drought_tolerance", "moderate"),
                frost_resistance=vit.get("frost_resistance", "moderate"),
                phylloxera_resistant=vit.get("phylloxera_resistant", False),
                can_grow_ungrafted=vit.get("can_grow_ungrafted", False),
                typical_rootstocks=vit.get("typical_rootstocks", []),
                # Winemaking attributes
                oxidative_style_suitable=wm.get("oxidative_style_suitable", False),
                skin_contact_suitable=wm.get("skin_contact_suitable", False),
                sparkling_suitable=wm.get("sparkling_suitable", False),
                fortified_suitable=wm.get("fortified_suitable", False),
                late_harvest_suitable=wm.get("late_harvest_suitable", False),
                carbonic_maceration=wm.get("carbonic_maceration", False),
                organic_suitability=wm.get("organic_suitability", "moderate"),
                biodynamic_affinity=wm.get("biodynamic_affinity", "moderate"),
                natural_wine_suitable=wm.get("natural_wine_suitable", False),
                amphora_suitable=wm.get("amphora_suitable", False),
                # Classification
                is_indigenous=g.get("is_indigenous", False),
                is_international=g.get("is_international", False),
                is_hybrid=g.get("is_hybrid", False),
                is_table_grape=g.get("is_table_grape", False),
                endangered=g.get("endangered", False),
            )
            self.varieties.append(variety)
            self._by_name[variety.name.lower()] = variety
            for alias in variety.aliases:
                self._by_name[alias.lower()] = variety

    def get(self, name: str) -> GrapeVariety | None:
        """Look up a grape by name or alias (case-insensitive)."""
        return self._by_name.get(name.lower())

    def red_grapes(self) -> list[GrapeVariety]:
        return [g for g in self.varieties if g.color == "red"]

    def white_grapes(self) -> list[GrapeVariety]:
        return [g for g in self.varieties if g.color == "white"]

    def by_region(self, region_name: str) -> list[GrapeVariety]:
        """Find grapes commonly grown in a region."""
        region_lower = region_name.lower()
        return [
            g for g in self.varieties
            if any(region_lower in r.lower() for r in g.key_regions)
        ]

    def indigenous_grapes(self) -> list[GrapeVariety]:
        return [g for g in self.varieties if g.is_indigenous]

    def international_grapes(self) -> list[GrapeVariety]:
        return [g for g in self.varieties if g.is_international]

    def natural_wine_grapes(self) -> list[GrapeVariety]:
        return [g for g in self.varieties if g.natural_wine_suitable]

    def sparkling_grapes(self) -> list[GrapeVariety]:
        return [g for g in self.varieties if g.sparkling_suitable]

    def endangered_grapes(self) -> list[GrapeVariety]:
        return [g for g in self.varieties if g.endangered]

    def by_climate(self, climate: str) -> list[GrapeVariety]:
        """Find grapes suited to a climate type."""
        climate_lower = climate.lower()
        return [
            g for g in self.varieties
            if any(climate_lower in c.lower() for c in g.climate_preferences)
        ]
