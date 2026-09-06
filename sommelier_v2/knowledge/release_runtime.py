"""Bridge simulated cellar state to reviewed protected-origin release rules.

The legal specification layer already contains release constraints. This module
supplies only values the process engine actually knows and keeps analytical or
calendar evidence explicit when the simulator cannot establish it safely.

No legal minimum is satisfied by a qualitative style label, an oak name, or an
assumed measurement. Unknown finished-wine total acidity, dry extract, total
alcoholic strength, wood-aging duration, bottle-aging duration, and calendar
release evidence remain unknown until supplied.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .cellar_pipeline import CellarPipelineResult
from .legal_practice_bridge import LegalPracticeBridge
from .legal_specs import LegalSpecRegistry, LegalWineSpec, ReleaseDecision


class ReleaseRuntimeConstraintError(ValueError):
    """Raised when claimed release evidence is internally inconsistent."""


@dataclass(frozen=True)
class ReleaseRuntimeInputs:
    total_aging_months: int
    wood_aging_months: int = 0
    bottle_aging_months: int = 0

    method: str | None = None
    manual_harvest: bool | None = None

    # Finished-wine analytical values that the current cellar model does not
    # establish with sufficient authority for legal compliance.
    total_alcohol_pct: float | None = None
    total_acidity_g_l: float | None = None
    dry_extract_g_l: float | None = None

    vintage_year: int | None = None
    elevage_end_date: date | None = None
    release_date: date | None = None
    require_complete: bool = True

    def __post_init__(self) -> None:
        for name, value in (
            ("total_aging_months", self.total_aging_months),
            ("wood_aging_months", self.wood_aging_months),
            ("bottle_aging_months", self.bottle_aging_months),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ReleaseRuntimeConstraintError(f"{name} must be a non-negative integer")
        if self.wood_aging_months + self.bottle_aging_months > self.total_aging_months:
            raise ReleaseRuntimeConstraintError(
                "wood_aging_months + bottle_aging_months cannot exceed total_aging_months"
            )
        for name, value, high in (
            ("total_alcohol_pct", self.total_alcohol_pct, 40.0),
            ("total_acidity_g_l", self.total_acidity_g_l, 40.0),
            ("dry_extract_g_l", self.dry_extract_g_l, 400.0),
        ):
            if value is not None and not 0.0 <= value <= high:
                raise ReleaseRuntimeConstraintError(f"{name} must be within 0..{high:g}")
        if self.vintage_year is not None and not 1600 <= self.vintage_year <= 3000:
            raise ReleaseRuntimeConstraintError("vintage_year must be within 1600..3000")
        if self.elevage_end_date is not None and self.release_date is not None:
            if self.release_date < self.elevage_end_date:
                raise ReleaseRuntimeConstraintError("release_date cannot precede elevage_end_date")
        if self.vintage_year is not None:
            for name, value in (
                ("elevage_end_date", self.elevage_end_date),
                ("release_date", self.release_date),
            ):
                if value is not None and value.year < self.vintage_year:
                    raise ReleaseRuntimeConstraintError(
                        f"{name} cannot precede the supplied vintage year"
                    )


def _selected_option(pipeline: CellarPipelineResult, decision_id: str) -> str | None:
    values = {
        application.option_id
        for application in pipeline.decision_runtime.applications
        if application.decision_id == decision_id
    }
    if not values:
        return None
    if len(values) > 1:
        raise ReleaseRuntimeConstraintError(
            f"Multiple {decision_id!r} selections are present in one decision runtime"
        )
    return next(iter(values))


def _manual_harvest(
    pipeline: CellarPipelineResult,
    explicit: bool | None,
) -> bool | None:
    if explicit is not None:
        return explicit
    selected = _selected_option(pipeline, "harvest-method")
    if selected == "hand":
        return True
    if selected == "machine":
        return False
    return None


def _production_method(
    spec: LegalWineSpec,
    pipeline: CellarPipelineResult,
    explicit: str | None,
) -> str | None:
    if explicit is not None:
        return explicit
    selected = _selected_option(pipeline, "sparkling-secondary")
    if selected is None or not spec.required_method:
        return None
    assessment = LegalPracticeBridge().assess_option(spec, "sparkling-secondary", selected)
    if assessment.legal_confirmation is True:
        # Use the exact reviewed legal vocabulary once the explicit selected
        # option has been proven equivalent by the narrow legal bridge.
        return spec.required_method
    return None


def _runtime_consistency_issues(
    pipeline: CellarPipelineResult,
    inputs: ReleaseRuntimeInputs,
) -> list[str]:
    issues: list[str] = []
    if not pipeline.fermentation.alcoholic_completed:
        issues.append("Alcoholic fermentation is not complete enough for release validation")

    if inputs.wood_aging_months > 0:
        if pipeline.maturation is None:
            issues.append(
                "Wood aging was claimed but the executed cellar pipeline contains no maturation stage"
            )
        else:
            duration_days = pipeline.decision_runtime.maturation_plan.duration_days
            # Any calendar month contains at least 28 days. This check only
            # rejects physically impossible claims; it does not convert days to
            # legal calendar months.
            if inputs.wood_aging_months * 28.0 > duration_days + 1e-9:
                issues.append(
                    "Claimed wood-aging months exceed the executed maturation duration even under a 28-day-per-month lower bound"
                )
    return issues


def validate_cellar_release(
    spec: LegalWineSpec,
    pipeline: CellarPipelineResult,
    inputs: ReleaseRuntimeInputs,
    *,
    registry: LegalSpecRegistry | None = None,
) -> ReleaseDecision:
    """Validate legal release using actual cellar outputs plus explicit evidence."""
    issues = _runtime_consistency_issues(pipeline, inputs)
    legal = registry or LegalSpecRegistry()

    elevage = inputs.elevage_end_date
    release = inputs.release_date
    decision = legal.validate_release(
        spec,
        total_aging_months=inputs.total_aging_months,
        wood_aging_months=inputs.wood_aging_months,
        bottle_aging_months=inputs.bottle_aging_months,
        method=_production_method(spec, pipeline, inputs.method),
        manual_harvest=_manual_harvest(pipeline, inputs.manual_harvest),
        final_alcohol_pct=pipeline.fermentation.final_ethanol_pct,
        total_alcohol_pct=inputs.total_alcohol_pct,
        total_acidity_g_l=inputs.total_acidity_g_l,
        dry_extract_g_l=inputs.dry_extract_g_l,
        residual_sugar_g_l=pipeline.fermentation.final_sugar_g_l,
        malic_acid_g_l=pipeline.fermentation.final_malic_acid_g_l,
        vintage_year=inputs.vintage_year,
        elevage_end_year=elevage.year if elevage else None,
        elevage_end_month=elevage.month if elevage else None,
        elevage_end_day=elevage.day if elevage else None,
        release_year=release.year if release else None,
        release_month=release.month if release else None,
        release_day=release.day if release else None,
        require_complete=inputs.require_complete,
    )
    combined = tuple(issues) + tuple(decision.issues)
    return ReleaseDecision(
        eligible=not combined,
        spec_id=spec.id,
        issues=combined,
    )
