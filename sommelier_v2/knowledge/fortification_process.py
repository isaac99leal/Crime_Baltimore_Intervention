"""End-to-end fermentation-arrest to physical fortification bridge.

The fermentation engine can stop kinetics at a requested residual-sugar target,
but its ``fortification`` arrest method does not itself add spirit. This bridge
runs the exact fermentation plan, verifies that fortification is the requested
arrest mechanism, and only after a successful arrest applies the separate
physical fortification mass balance.

The pre-fortification liquid volume is mandatory. Fermentation does not yet
establish a sufficiently exact recovered liquid volume to manufacture one.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real

from .fermentation_process import (
    FermentationPlan,
    FermentationResult,
    MustComposition,
    run_fermentation,
)
from .fortification_chemistry import (
    FortificationLiquid,
    FortificationPostMixMeasurements,
    FortificationResult,
    fortify_liquid,
)


class FortificationProcessConstraintError(ValueError):
    """Raised for an internally inconsistent fermentation→fortification plan."""


def _positive_real(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise FortificationProcessConstraintError(
            f"{name} must be a real numeric value; got {value!r}"
        )
    number = float(value)
    if not isfinite(number) or number <= 0:
        raise FortificationProcessConstraintError(
            f"{name} must be finite and positive; got {value!r}"
        )
    return number


@dataclass(frozen=True)
class PreFortificationMeasurements:
    """Optional measured chemistry at the physical moment before spirit addition."""

    tartaric_acid_g_l: float | None = None
    total_so2_mg_l: float | None = None
    ph: float | None = None
    free_so2_mg_l: float | None = None
    titratable_acidity_g_l: float | None = None


@dataclass(frozen=True)
class FortificationArrestResult:
    status: str
    completed: bool
    fermentation: FermentationResult
    pre_fortification_liquid: FortificationLiquid | None
    fortification: FortificationResult | None
    warnings: tuple[str, ...] = ()


def run_fortification_arrest(
    must: MustComposition,
    plan: FermentationPlan,
    spirit: FortificationLiquid,
    *,
    base_source_id: str,
    pre_fortification_volume_l: float,
    pre_fortification: PreFortificationMeasurements | None = None,
    post_mix: FortificationPostMixMeasurements | None = None,
) -> FortificationArrestResult:
    """Run a fortification-arrest plan and physically add spirit if arrest succeeds.

    This helper is specifically for sweet-wine fermentation arrest. Dry or
    post-fermentation fortification should call :func:`fortify_liquid` directly.
    """

    if plan.arrest_method != "fortification":
        raise FortificationProcessConstraintError(
            "run_fortification_arrest requires plan.arrest_method == 'fortification'."
        )
    if plan.target_residual_sugar_g_l <= 2.0:
        raise FortificationProcessConstraintError(
            "Fermentation-arrest fortification requires a residual-sugar target above 2 g/L; use fortify_liquid directly for dry/post-fermentation fortification."
        )
    if plan.malolactic:
        raise FortificationProcessConstraintError(
            "MLF cannot be simulated inside this fortification-arrest bridge because the current MLF model would run before the physical spirit addition and at the wrong ethanol concentration."
        )
    if not isinstance(base_source_id, str) or not base_source_id.strip():
        raise FortificationProcessConstraintError("base_source_id is required.")
    volume = _positive_real("pre_fortification_volume_l", pre_fortification_volume_l)

    fermentation = run_fermentation(must, plan)
    if not fermentation.arrested or fermentation.stuck:
        warnings = list(fermentation.warnings)
        warnings.append(
            "Physical spirit addition was not applied because fermentation did not reach the requested fortification-arrest point."
        )
        return FortificationArrestResult(
            status="fermentation_not_ready_for_fortification",
            completed=False,
            fermentation=fermentation,
            pre_fortification_liquid=None,
            fortification=None,
            warnings=tuple(warnings),
        )

    measurements = pre_fortification or PreFortificationMeasurements()
    base = FortificationLiquid(
        source_id=base_source_id,
        volume_l=volume,
        ethanol_pct=fermentation.final_ethanol_pct,
        residual_sugar_g_l=fermentation.final_sugar_g_l,
        malic_acid_g_l=fermentation.final_malic_acid_g_l,
        lactic_acid_g_l=fermentation.final_lactic_acid_g_l,
        tartaric_acid_g_l=measurements.tartaric_acid_g_l,
        volatile_acidity_g_l=fermentation.final_volatile_acidity_g_l,
        total_so2_mg_l=measurements.total_so2_mg_l,
        ph=measurements.ph,
        free_so2_mg_l=measurements.free_so2_mg_l,
        titratable_acidity_g_l=measurements.titratable_acidity_g_l,
    )
    fortified = fortify_liquid(base, spirit, post_mix=post_mix)
    return FortificationArrestResult(
        status="fortified_after_arrest",
        completed=True,
        fermentation=fermentation,
        pre_fortification_liquid=base,
        fortification=fortified,
        warnings=tuple(fermentation.warnings) + tuple(fortified.warnings),
    )
