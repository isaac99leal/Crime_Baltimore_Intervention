"""Bridge packaging state into the continuous bottle-aging model.

Bottle aging is downstream of packaging. The packaging layer can only quantify
oxygen exposure when the needed measurements/priors are supplied explicitly.
This bridge therefore fails closed by default when packaging oxygen is incomplete
and refuses to invent packaging chemistry for commercial inventory that lacks a
stored bottling snapshot.

Storage, bottle size, and longevity modifiers are explicit simulator inputs.
They are not inferred from producer identity, physical bottle volume, appellation,
price, or closure name.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..domain import InventoryLot, InventoryPackagingSnapshot
from .aging import state_at_age
from .cellar_pipeline import CellarPipelineResult
from .schema import AgingArchetype, AgingState


class BottleLifecycleConstraintError(ValueError):
    """Raised when bottle-age execution would rely on an unsupported state."""


@dataclass(frozen=True)
class BottleAgingPlan:
    age_years: float
    longevity_modifier: float = 1.0
    storage_modifier: float = 1.0
    bottle_size_modifier: float = 1.0
    require_complete_packaging_oxygen: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.age_years <= 250.0:
            raise BottleLifecycleConstraintError("age_years must be within 0..250")
        for name, value in (
            ("longevity_modifier", self.longevity_modifier),
            ("storage_modifier", self.storage_modifier),
            ("bottle_size_modifier", self.bottle_size_modifier),
        ):
            if not 0.1 <= value <= 10.0:
                raise BottleLifecycleConstraintError(f"{name} must be within 0.1..10")


@dataclass(frozen=True)
class BottleAgingResult:
    state: AgingState
    packaging_oxygen_modifier: float
    packaging_oxygen_complete: bool
    conditional_on_incomplete_oxygen: bool
    warnings: tuple[str, ...] = ()


def _age_from_packaging_state(
    archetype: AgingArchetype,
    plan: BottleAgingPlan,
    *,
    oxygen_assessment_complete: bool,
    ageing_oxygen_modifier: float,
    tartrate_physical_instability_risk: float | None,
    inherited_warnings: tuple[str, ...] = (),
) -> BottleAgingResult:
    if plan.require_complete_packaging_oxygen and not oxygen_assessment_complete:
        raise BottleLifecycleConstraintError(
            "Bottle aging requires complete packaging oxygen evidence: both measured pre-bottling "
            "dissolved oxygen and an explicit closure oxygen-exposure prior are required."
        )

    warnings = list(inherited_warnings)
    conditional = not oxygen_assessment_complete
    if conditional:
        warnings.append(
            "Bottle-aging oxygen trajectory is conditional because packaging oxygen assessment is incomplete."
        )
    if tartrate_physical_instability_risk is None:
        warnings.append("Tartrate stability remains unknown during the bottle-aging simulation.")
    elif tartrate_physical_instability_risk >= 1.0:
        warnings.append("The bottled wine is test-confirmed tartrate-unstable.")

    state = state_at_age(
        archetype,
        plan.age_years,
        longevity_modifier=plan.longevity_modifier,
        storage_modifier=plan.storage_modifier,
        oxygen_modifier=ageing_oxygen_modifier,
        bottle_size_modifier=plan.bottle_size_modifier,
    )
    return BottleAgingResult(
        state=state,
        packaging_oxygen_modifier=ageing_oxygen_modifier,
        packaging_oxygen_complete=oxygen_assessment_complete,
        conditional_on_incomplete_oxygen=conditional,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def age_cellar_wine(
    archetype: AgingArchetype,
    cellar: CellarPipelineResult,
    plan: BottleAgingPlan,
) -> BottleAgingResult:
    """Age a cellar result using its packaging oxygen assessment.

    The packaging oxygen modifier is the only packaging-to-aging transfer. A
    maturation dissolved-oxygen state is not reused because bottling operations
    can materially change oxygen exposure.
    """
    packaging = cellar.packaging
    return _age_from_packaging_state(
        archetype,
        plan,
        oxygen_assessment_complete=packaging.oxygen_assessment_complete,
        ageing_oxygen_modifier=packaging.ageing_oxygen_modifier,
        tartrate_physical_instability_risk=packaging.tartrate_physical_instability_risk,
        inherited_warnings=tuple(packaging.warnings),
    )


def age_inventory_lot(
    archetype: AgingArchetype,
    lot: InventoryLot,
    plan: BottleAgingPlan,
) -> BottleAgingResult:
    """Age commercial bottle inventory from its stored packaging snapshot.

    Missing packaging state is not converted into a neutral oxygen modifier. For
    legacy/imported stock, callers must first attach an explicit defensible
    ``InventoryPackagingSnapshot`` or avoid chemistry-conditioned bottle aging.
    Physical ``lot.bottle_ml`` is retained as fact but is not translated into the
    plan's bottle-size modifier automatically.
    """
    snapshot: InventoryPackagingSnapshot | None = lot.packaging_snapshot
    if snapshot is None:
        raise BottleLifecycleConstraintError(
            "Commercial inventory lot has no packaging chemistry snapshot; bottle-aging oxygen state cannot be inferred."
        )
    return _age_from_packaging_state(
        archetype,
        plan,
        oxygen_assessment_complete=snapshot.oxygen_assessment_complete,
        ageing_oxygen_modifier=snapshot.ageing_oxygen_modifier,
        tartrate_physical_instability_risk=snapshot.tartrate_physical_instability_risk,
        inherited_warnings=tuple(snapshot.warnings),
    )
