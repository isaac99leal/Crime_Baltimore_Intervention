"""Core domain models for Sommelier Simulator v2.

The v2 engine keeps business state independent from any UI toolkit. Pygame,
a web client, or a future native client can all drive the same simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class WineStyle(str, Enum):
    RED = "Red"
    WHITE = "White"
    ROSE = "Rosé"
    SPARKLING = "Sparkling"
    DESSERT = "Dessert"
    FORTIFIED = "Fortified"
    ORANGE = "Orange"
    OTHER = "Other"


class SalesChannel(str, Enum):
    BOTTLE = "bottle"
    BTG = "btg"
    OFF_MENU = "off_menu"


class RelationshipKind(str, Enum):
    DISTRIBUTOR = "distributor"
    IMPORTER = "importer"
    GROWER = "grower"
    BROKER = "broker"


@dataclass(frozen=True)
class WineRecord:
    """Immutable commercial and sensory identity for one wine/vintage."""

    id: str
    producer: str
    label: str
    country: str
    region: str
    subregion: str = ""
    appellation: str = ""
    vineyard: str = ""
    vintage: int = 0
    style: WineStyle = WineStyle.OTHER
    grapes: tuple[str, ...] = ()
    classification: str = ""
    wholesale_cost: float = 0.0
    rarity: float = 0.0
    acidity: float = 3.0
    tannin: float = 3.0
    body: float = 3.0
    sweetness: float = 1.0
    alcohol: float = 13.0
    fruit_intensity: float = 3.0
    earth_intensity: float = 2.0
    oak_influence: float = 2.0
    aromas: tuple[str, ...] = ()
    winemaking_notes: str = ""
    farming_notes: str = ""
    drink_window_start: int = 0
    drink_window_end: int = 0
    is_organic: bool = False
    is_biodynamic: bool = False
    is_natural: bool = False
    is_ungrafted: bool = False
    is_old_vine: bool = False

    @property
    def display_name(self) -> str:
        parts = [str(self.vintage) if self.vintage else "NV", self.producer]
        if self.label and self.label.lower() != self.producer.lower():
            parts.append(self.label)
        if self.vineyard:
            parts.append(self.vineyard)
        return " ".join(part for part in parts if part)


@dataclass
class OpenBottleState:
    """One physically opened bottle and its independent service-age clock.

    ``opened_day=None`` is permitted only for migrated legacy state whose true
    opening date is unknown. Inventory logic must preserve that uncertainty
    rather than assigning a fabricated date.
    """

    remaining_ml: int
    opened_day: int | None

    def __post_init__(self) -> None:
        if self.remaining_ml <= 0:
            raise ValueError("open bottle remaining_ml must be positive")
        if self.opened_day is not None and self.opened_day < 0:
            raise ValueError("opened_day cannot be negative")


@dataclass(frozen=True)
class InventoryProvenanceComponent:
    """Normalized physical provenance carried into commercial inventory."""

    volume_pct: float
    grape: str
    country: str
    origins: tuple[str, ...]
    vintage: int | None
    block_ids: tuple[str, ...] = ()
    source_lot_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.volume_pct <= 0.0 or self.volume_pct > 100.0 + 1e-9:
            raise ValueError("provenance component volume_pct must be within (0, 100]")
        if not self.grape.strip() or not self.country.strip():
            raise ValueError("provenance component requires grape and country")


@dataclass
class InventoryLot:
    """A purchasable lot, including BTG and physical provenance state.

    ``open_bottle_ml`` and ``opened_day`` remain as compatibility fields for old
    saves and callers. When ``open_bottles`` is populated, the per-bottle queue is
    authoritative and the inventory manager keeps the legacy aggregate fields in
    sync.
    """

    lot_id: str
    wine: WineRecord
    sealed_bottles: int
    unit_cost: float
    received_day: int
    supplier_id: str = ""
    reserved_bottles: int = 0
    storage_zone: str = "main_cellar"
    storage_temp_f: float = 55.0
    storage_humidity_pct: float = 68.0
    listed_bottle: bool = False
    listed_btg: bool = False
    list_price_bottle: float = 0.0
    list_price_glass: float = 0.0
    bottle_ml: int = 750
    glass_ml: int = 150
    open_bottle_ml: int = 0
    opened_day: int | None = None
    open_bottle_life_days: int = 3
    open_bottles: list[OpenBottleState] = field(default_factory=list)
    source_winery_lot_id: str = ""
    source_dispatch_reference: str = ""
    provenance_fingerprint: str = ""
    provenance_components: tuple[InventoryProvenanceComponent, ...] = ()

    @property
    def available_sealed_bottles(self) -> int:
        return max(0, self.sealed_bottles - self.reserved_bottles)

    @property
    def open_volume_ml(self) -> int:
        if self.open_bottles:
            return sum(bottle.remaining_ml for bottle in self.open_bottles)
        return max(0, self.open_bottle_ml)

    @property
    def bottle_equivalents(self) -> float:
        return self.sealed_bottles + (self.open_volume_ml / self.bottle_ml)

    @property
    def inventory_cost_value(self) -> float:
        return self.unit_cost * self.bottle_equivalents


@dataclass
class MenuPlacement:
    wine_id: str
    channel: SalesChannel
    price: float
    section: str = ""
    sort_order: int = 0
    tasting_note: str = ""
    pairing_note: str = ""
    active: bool = True
    printed: bool = True


@dataclass
class WineListEdition:
    edition: int = 1
    printed_day: int = 1
    reprint_cost: float = 0.0
    placements: list[MenuPlacement] = field(default_factory=list)

    def active_placements(self, channel: SalesChannel | None = None) -> list[MenuPlacement]:
        items = [p for p in self.placements if p.active]
        if channel is not None:
            items = [p for p in items if p.channel == channel]
        return items


@dataclass
class RelationshipAccount:
    id: str
    name: str
    kind: RelationshipKind = RelationshipKind.DISTRIBUTOR
    trust: float = 35.0
    access: float = 25.0
    reliability: float = 70.0
    spend_ytd: float = 0.0
    support_score: float = 0.0
    last_contact_day: int = 0
    late_payments: int = 0
    events_supported: int = 0
    exclusivity_pressure: float = 0.0

    def clamp(self) -> None:
        self.trust = max(0.0, min(100.0, self.trust))
        self.access = max(0.0, min(100.0, self.access))
        self.reliability = max(0.0, min(100.0, self.reliability))
        self.support_score = max(0.0, min(100.0, self.support_score))
        self.exclusivity_pressure = max(0.0, min(100.0, self.exclusivity_pressure))


@dataclass(frozen=True)
class AllocationOffer:
    allocation_id: str
    supplier_id: str
    wine: WineRecord
    offered_bottles: int
    unit_cost: float
    scarcity: float
    required_support_spend: float = 0.0
    deadline_day: int = 0


@dataclass
class StaffMember:
    id: str
    name: str
    role: str
    hourly_cost: float
    wine_knowledge: float = 20.0
    service_skill: float = 50.0
    sales_skill: float = 45.0
    reliability: float = 75.0
    morale: float = 70.0
    training_points: float = 0.0

    def train(self, points: float) -> None:
        self.training_points += max(0.0, points)
        gain = max(0.0, points) * 0.08
        self.wine_knowledge = min(100.0, self.wine_knowledge + gain)
        self.service_skill = min(100.0, self.service_skill + gain * 0.35)
        self.morale = min(100.0, self.morale + gain * 0.15)


@dataclass
class EquipmentAsset:
    id: str
    name: str
    category: str
    purchase_price: float
    quality: float = 50.0
    maintenance_per_week: float = 0.0
    capacity_bonus_bottles: int = 0
    btg_waste_reduction: float = 0.0
    service_speed_bonus: float = 0.0


@dataclass
class CredentialProgress:
    track: str
    level: int = 0
    theory: float = 0.0
    tasting: float = 0.0
    service: float = 0.0
    attempts: int = 0

    @property
    def readiness(self) -> float:
        return (self.theory + self.tasting + self.service) / 3.0


@dataclass
class CareerState:
    reputation: float = 10.0
    salary_per_week: float = 650.0
    title: str = "Wine Steward"
    credentials: dict[str, CredentialProgress] = field(default_factory=dict)

    def add_reputation(self, delta: float) -> None:
        self.reputation = max(0.0, min(100.0, self.reputation + delta))


@dataclass(frozen=True)
class GuestProfile:
    id: str
    name: str
    budget_per_bottle: float
    preferred_styles: tuple[WineStyle, ...] = ()
    preferred_grapes: tuple[str, ...] = ()
    preferred_regions: tuple[str, ...] = ()
    body_preference: float = 3.0
    sweetness_preference: float = 1.0
    adventurousness: float = 0.5
    prestige_sensitivity: float = 0.5
    value_sensitivity: float = 0.5
    patience: float = 0.7


@dataclass
class BeverageProgram:
    """Persistent restaurant beverage-program state."""

    name: str
    cash: float = 25_000.0
    day: int = 1
    week: int = 1
    cellar_capacity_bottles: int = 600
    reputation: float = 15.0
    inventory: dict[str, InventoryLot] = field(default_factory=dict)
    relationships: dict[str, RelationshipAccount] = field(default_factory=dict)
    staff: dict[str, StaffMember] = field(default_factory=dict)
    equipment: dict[str, EquipmentAsset] = field(default_factory=dict)
    wine_list: WineListEdition = field(default_factory=WineListEdition)
    career: CareerState = field(default_factory=CareerState)
    time_blocks_remaining: int = 12

    @property
    def bottles_in_cellar(self) -> float:
        return sum(lot.bottle_equivalents for lot in self.inventory.values())

    @property
    def cellar_space_remaining(self) -> float:
        return max(0.0, self.cellar_capacity_bottles - self.bottles_in_cellar)

    @property
    def inventory_value(self) -> float:
        return sum(lot.inventory_cost_value for lot in self.inventory.values())

    def spend_time(self, blocks: int) -> bool:
        if blocks < 0:
            raise ValueError("blocks must be non-negative")
        if blocks > self.time_blocks_remaining:
            return False
        self.time_blocks_remaining -= blocks
        return True

    def reset_day(self) -> None:
        self.day += 1
        self.week = ((self.day - 1) // 7) + 1
        self.time_blocks_remaining = 12

    def add_relationships(self, relationships: Iterable[RelationshipAccount]) -> None:
        for relationship in relationships:
            self.relationships[relationship.id] = relationship
