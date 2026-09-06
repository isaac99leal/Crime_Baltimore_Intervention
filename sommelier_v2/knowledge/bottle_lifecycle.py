"""Bridge packaging state into the continuous bottle-aging model.

Bottle aging is downstream of packaging. The existing packaging layer can only
quantify oxygen exposure when both pre-bottling dissolved oxygen and closure
oxygen behavior are supplied explicitly. This bridge therefore fails closed by
default when packaging oxygen is incomplete.

Storage, bottle size, and longevity modifiers are explicit simulator inputs.
They are not inferred from producer identity, bottle format names, appellation,
or price.
"""
from __future__ import annotations

from dataclasses import dataclass

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
    if plan.require_complete_packaging_oxygen and not packaging.oxygen_assessment_complete:
        raise BottleLifecycleConstraintError(
            "Bottle aging requires complete packaging oxygen evidence: both measured pre-bottling "
            "dissolved oxygen and an explicit closure oxygen-exposure prior are required."
        )

    warnings: list[str] = []
    conditional = not packaging.oxygen_assessment_complete
    if conditional:
        warnings.append(
            "Bottle-aging oxygen trajectory is conditional because packaging oxygen assessment is incomplete."
        )
    if packaging.tartrate_physical_instability_risk is None:
        warnings.append("Tartrate stability remains unknown during the bottle-aging simulation.")
    elif packaging.tartrate_physical_instability_risk >= 1.0:
        warnings.append("The bottled wine is test-confirmed tartrate-unstable.")

    oxygen_modifier = packaging.ageing_oxygen_modifier
    state = state_at_age(
        archetype,
        plan.age_years,
        longevity_modifier=plan.longevity_modifier,
        storage_modifier=plan.storage_modifier,
        oxygen_modifier=oxygen_modifier,
        bottle_size_modifier=plan.bottle_size_modifier,
    )
    return BottleAgingResult(
        state=state,
        packaging_oxygen_modifier=oxygen_modifier,
        packaging_oxygen_complete=packaging.oxygen_assessment_complete,
        conditional_on_incomplete_oxygen=conditional,
        warnings=tuple(warnings),
    )
