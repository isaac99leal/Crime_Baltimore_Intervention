"""Sommelier Simulator: unified game and simulation-first beverage engine."""

from .authoritative_catalog import (
    AuthoritativeCatalogGenerator,
    AuthoritativeCatalogItem,
    AuthoritativeCatalogReport,
    LEGAL_SNAPSHOT_AS_OF_YEAR,
)
from .catalog import CatalogIndex, load_catalog, load_default_catalog, load_legacy_catalog
from .commercial_provenance import (
    CommercialDispatchResult,
    CommercialProvenanceError,
    dispatch_winery_lot_to_inventory,
    inventory_provenance_components,
    provenance_fingerprint,
)
from .domain import (
    BeverageProgram,
    CareerState,
    EquipmentAsset,
    GuestProfile,
    InventoryLot,
    InventoryProvenanceComponent,
    MenuPlacement,
    OpenBottleState,
    RelationshipAccount,
    StaffMember,
    WineRecord,
    WineStyle,
)
from .generation import (
    ConstrainedWineBuilder,
    GeneratedWine,
    WineBuildRequest,
    WineProductionConstraintError,
    WineReleaseConstraintError,
)
from .knowledge.bottling_lot import BottledLotManifest, BottlingLotConstraintError, bottle_winery_lot
from .knowledge.finished_wine import FinishedWineAssembler, FinishedWineConstraintError, ValidatedWineRecord
from .knowledge.winery_provenance import ProvenanceSlice, WineryLot, WineryProvenanceError, WineryProvenanceLedger
from .simulation import RestaurantSimulation
from .unified_game import UnifiedGameState
from .wine_registry import REGISTRY_DISPLAY_NAME, SommelierWorldRegistry

__all__ = [
    "AuthoritativeCatalogGenerator",
    "AuthoritativeCatalogItem",
    "AuthoritativeCatalogReport",
    "BeverageProgram",
    "BottledLotManifest",
    "BottlingLotConstraintError",
    "CareerState",
    "CatalogIndex",
    "CommercialDispatchResult",
    "CommercialProvenanceError",
    "ConstrainedWineBuilder",
    "EquipmentAsset",
    "FinishedWineAssembler",
    "FinishedWineConstraintError",
    "GeneratedWine",
    "GuestProfile",
    "InventoryLot",
    "InventoryProvenanceComponent",
    "LEGAL_SNAPSHOT_AS_OF_YEAR",
    "MenuPlacement",
    "OpenBottleState",
    "ProvenanceSlice",
    "REGISTRY_DISPLAY_NAME",
    "RelationshipAccount",
    "RestaurantSimulation",
    "SommelierWorldRegistry",
    "StaffMember",
    "UnifiedGameState",
    "ValidatedWineRecord",
    "WineBuildRequest",
    "WineProductionConstraintError",
    "WineRecord",
    "WineReleaseConstraintError",
    "WineStyle",
    "WineryLot",
    "WineryProvenanceError",
    "WineryProvenanceLedger",
    "bottle_winery_lot",
    "dispatch_winery_lot_to_inventory",
    "inventory_provenance_components",
    "load_catalog",
    "load_default_catalog",
    "load_legacy_catalog",
    "provenance_fingerprint",
]
