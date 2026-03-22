"""Wine and tasting profile data models."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class TastingProfile:
    """Numerical tasting attributes for a wine."""
    acidity: float = 3.0       # 1-5
    tannin: float = 3.0        # 1-5
    body: float = 3.0          # 1-5
    sweetness: float = 1.0     # 1-5
    alcohol: float = 13.0      # Actual percentage
    fruit_intensity: float = 3.0   # 1-5
    earth_intensity: float = 2.0   # 1-5
    oak_influence: float = 2.0     # 1-5
    primary_aromas: list[str] = field(default_factory=list)
    secondary_aromas: list[str] = field(default_factory=list)
    tertiary_aromas: list[str] = field(default_factory=list)
    color: str = "medium ruby"

    def similarity(self, other: TastingProfile) -> float:
        """Calculate how similar two profiles are (0-1, 1 = identical)."""
        attrs = ["acidity", "tannin", "body", "sweetness",
                 "fruit_intensity", "earth_intensity", "oak_influence"]
        total_diff = 0.0
        for attr in attrs:
            diff = abs(getattr(self, attr) - getattr(other, attr))
            total_diff += diff / 4.0  # Normalize to 0-1 range per attribute
        return max(0.0, 1.0 - (total_diff / len(attrs)))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> TastingProfile:
        return cls(**data)


@dataclass
class GrapeBlend:
    """A grape variety and its percentage in a blend."""
    grape: str
    percentage: float  # 0-100

    def to_dict(self) -> dict:
        return {"grape": self.grape, "percentage": self.percentage}

    @classmethod
    def from_dict(cls, data: dict) -> GrapeBlend:
        return cls(**data)


@dataclass
class Wine:
    """A single wine in the game world."""
    id: str
    producer_name: str
    estate_name: str
    region_path: list[str]       # ["France", "Burgundy", "Côte de Nuits", "Vosne-Romanée"]
    appellation: str             # The most specific appellation name
    classification: str          # "Grand Cru", "Premier Cru", "Village", "Regional", etc.
    grapes: list[GrapeBlend]
    vintage: int
    style: str                   # "Red", "White", "Rosé", "Sparkling", "Fortified", "Dessert"
    profile: TastingProfile
    aging_potential_years: int    # How many years this wine can age
    current_condition: str       # "Young", "Developing", "Approaching Peak", "Peak", "Past Peak", "Declining"
    wholesale_cost: float
    suggested_retail: float
    rarity: float                # 0.0-1.0
    quantity_available: int      # Bottles available from vendor
    vineyard_name: str = ""      # Specific vineyard/cru name if applicable
    special_designation: str = ""  # "Reserve", "Riserva", "Gran Reserva", "Einzellage", etc.
    winemaking_notes: str = ""   # "Aged 18 months in French oak", etc.
    drink_window_start: int = 0  # Vintage year + this = when to start drinking
    drink_window_end: int = 0    # Vintage year + this = when wine declines
    # Production methods and certifications
    is_organic: bool = False          # Certified organic viticulture
    is_biodynamic: bool = False       # Certified biodynamic (Demeter etc.)
    is_natural: bool = False          # Natural wine (minimal intervention, no/low SO2)
    is_ungrafted: bool = False        # From ungrafted/own-root vines (pre-phylloxera or sandy soil)
    is_orange_wine: bool = False      # White grapes with extended skin contact
    is_pet_nat: bool = False          # Pétillant naturel (ancestral method sparkling)
    is_amphora: bool = False          # Aged in clay amphora/qvevri
    is_old_vine: bool = False         # From old vines (vieilles vignes, typically 40+ years)
    vine_age_years: int = 0           # Average vine age in years
    sulfites_ppm: int = 0             # SO2 level (0 = not specified; natural wines typically <30)
    farming_notes: str = ""           # "Hand-harvested, no pesticides, cover crops"

    @property
    def country(self) -> str:
        return self.region_path[0] if self.region_path else "Unknown"

    @property
    def region(self) -> str:
        return self.region_path[1] if len(self.region_path) > 1 else self.country

    @property
    def full_name(self) -> str:
        """Generate display name for the wine."""
        parts = []
        if self.estate_name:
            parts.append(self.estate_name)
        if self.vineyard_name:
            parts.append(self.vineyard_name)
        elif self.appellation:
            parts.append(self.appellation)
        if self.special_designation:
            parts.append(self.special_designation)
        return " ".join(parts)

    @property
    def display_line(self) -> str:
        """One-line display: Vintage Name, Region — $price."""
        return f"{self.vintage} {self.full_name}, {self.region} — ${self.suggested_retail:.0f}"

    @property
    def grape_names(self) -> list[str]:
        return [g.grape for g in self.grapes]

    @property
    def primary_grape(self) -> str:
        if self.grapes:
            return max(self.grapes, key=lambda g: g.percentage).grape
        return "Unknown"

    def age_in_cellar(self, current_year: int) -> int:
        """Years since vintage."""
        return current_year - self.vintage

    def condition_at_year(self, year: int) -> str:
        """Determine condition based on age relative to drink window."""
        age = year - self.vintage
        if age < self.drink_window_start:
            if age < self.drink_window_start // 2:
                return "Young"
            return "Developing"
        elif age <= self.drink_window_end:
            mid = (self.drink_window_start + self.drink_window_end) / 2
            if age < mid:
                return "Approaching Peak"
            return "Peak"
        else:
            overage = age - self.drink_window_end
            if overage < 5:
                return "Past Peak"
            return "Declining"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["grapes"] = [g.to_dict() for g in self.grapes]
        d["profile"] = self.profile.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Wine:
        data["grapes"] = [GrapeBlend.from_dict(g) for g in data["grapes"]]
        data["profile"] = TastingProfile.from_dict(data["profile"])
        return cls(**data)


@dataclass
class CellarSlot:
    """A wine stored in the restaurant's cellar."""
    wine: Wine
    quantity: int
    purchase_price: float        # What we paid per bottle
    date_acquired: int           # Game day number
    storage_temp_f: float = 55.0
    storage_humidity: float = 70.0
    on_wine_list: bool = False
    list_price: float = 0.0      # Price on the wine list

    @property
    def total_value(self) -> float:
        return self.quantity * self.purchase_price

    @property
    def potential_revenue(self) -> float:
        return self.quantity * self.list_price if self.on_wine_list else 0.0

    def to_dict(self) -> dict:
        return {
            "wine": self.wine.to_dict(),
            "quantity": self.quantity,
            "purchase_price": self.purchase_price,
            "date_acquired": self.date_acquired,
            "storage_temp_f": self.storage_temp_f,
            "storage_humidity": self.storage_humidity,
            "on_wine_list": self.on_wine_list,
            "list_price": self.list_price,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CellarSlot:
        data["wine"] = Wine.from_dict(data["wine"])
        return cls(**data)
