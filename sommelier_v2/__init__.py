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
    dispatch_bottled_manifest_to_inventory,
    dispatch_winery_lot_to_inventory,
    inventory_provenance_components,
    packaging_snapshot_from_assessment,
    provenance_fingerprint,
)
from .domain import (
    BeverageProgram,
    CareerState,
    EquipmentAsset,
    GuestProfile,
    InventoryLot,
    InventoryPackagingSnapshot,
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
from .knowledge.blend_chemistry import (
    BlendChemistryComponent,
    BlendChemistryConstraintError,
    BlendChemistryResult,
    BlendPostMixMeasurements,
    blend_chemistry,
)
from .knowledge.bottle_lifecycle import age_inventory_lot
from .knowledge.bottling_lot import BottledLotManifest, BottlingLotConstraintError, bottle_winery_lot
from .knowledge.finished_wine import FinishedWineAssembler, FinishedWineConstraintError, ValidatedWineRecord
from .knowledge.winery_blend_chemistry import (
    WineryBlendChemistryConstraintError,
    WineryBlendChemistryResult,
    blend_winery_lots_with_chemistry,
)
from .knowledge.winery_provenance import ProvenanceSlice, WineryLot, WineryProvenanceError, WineryProvenanceLedger
from .simulation import RestaurantSimulation
from .unified_game import UnifiedGameState
from .wine_registry import REGISTRY_DISPLAY_NAME, SommelierWorldRegistry

__all__ = [
    "AuthoritativeCatalogGenerator",
    "AuthoritativeCatalogItem",
    "AuthoritativeCatalogReport",
    "BeverageProgram",
    "BlendChemistryComponent",
    "BlendChemistryConstraintError",
    "BlendChemistryResult",
    "BlendPostMixMeasurements",
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
    "InventoryPackagingSnapshot",
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
    "WineryBlendChemistryConstraintError",
    "WineryBlendChemistryResult",
    "WineryLot",
    "WineryProvenanceError",
    "WineryProvenanceLedger",
    "age_inventory_lot",
    "blend_chemistry",
    "blend_winery_lots_with_chemistry",
    "bottle_winery_lot",
    "dispatch_bottled_manifest_to_inventory",
    "dispatch_winery_lot_to_inventory",
    "inventory_provenance_components",
    "load_catalog",
    "load_default_catalog",
    "load_legacy_catalog",
    "packaging_snapshot_from_assessment",
    "provenance_fingerprint",
]
