"""Time-resolved skin-contact, cap-management, and pressing extraction mechanics.

This module is separate from alcoholic-fermentation kinetics. It consumes the
actual fermentation history so extraction responds to the realized temperature
and ethanol trajectory, but it does not make yeast growth depend on a sensory
matrix choice.

All numerical coefficients below are bounded simulator priors. OIV or other
practice references can establish that a cellar operation exists; they do not
supply these game coefficients or determine whether a protected designation
permits the operation.
"""
from __future__ import annotations

from dataclasses import dataclass

from .fermentation_engine import FermentationState, clamp


class ExtractionConstraintError(ValueError):
    """Raised when an extraction plan contains an invalid physical state."""


@dataclass(frozen=True)
class CapManagementEvent:
    hour: float
    intensity: float
    method: str = "unspecified"

    def __post_init__(self) -> None:
        if self.hour < 0.0:
            raise ExtractionConstraintError("Cap-management event hour must be non-negative")
        if not 0.0 <= self.intensity <= 1.0:
            raise ExtractionConstraintError("Cap-management event intensity must be within 0..1")
        if not self.method.strip():
            raise ExtractionConstraintError("Cap-management event method cannot be blank")


@dataclass(frozen=True)
class ExtractionPlan:
    maceration_start_hour: float = 0.0
    maceration_end_hour: float | None = None
    cap_management_events: tuple[CapManagementEvent, ...] = ()
    baseline_extraction_scale: float = 1.0
    press_wine_blend_fraction: float = 0.0
    press_severity: float = 0.0

    def __post_init__(self) -> None:
        if self.maceration_start_hour < 0.0:
            raise ExtractionConstraintError("maceration_start_hour must be non-negative")
        if self.maceration_end_hour is not None and self.maceration_end_hour < self.maceration_start_hour:
            raise ExtractionConstraintError("maceration_end_hour cannot precede maceration_start_hour")
        if not 0.0 <= self.baseline_extraction_scale <= 3.0:
            raise ExtractionConstraintError("baseline_extraction_scale must be within 0..3")
        if not 0.0 <= self.press_wine_blend_fraction <= 1.0:
            raise ExtractionConstraintError("press_wine_blend_fraction must be within 0..1")
        if not 0.0 <= self.press_severity <= 1.0:
            raise ExtractionConstraintError("press_severity must be within 0..1")
        prior_hour = -1.0
        for event in self.cap_management_events:
            if event.hour < prior_hour:
                raise ExtractionConstraintError("cap_management_events must be ordered by hour")
            prior_hour = event.hour


@dataclass(frozen=True)
class ExtractionPoint:
    hour: float
    anthocyanin_index: float
    tannin_index: float
    phenolic_index: float
    cap_event_load: float = 0.0


@dataclass(frozen=True)
class ExtractionResult:
    anthocyanin_index: float
    tannin_index: float
    phenolic_index: float
    skin_contact_hours: float
    cap_event_count: int
    ignored_cap_event_count: int
    press_tannin_increment: float
    press_phenolic_increment: float
    curve: tuple[ExtractionPoint, ...]
    warnings: tuple[str, ...] = ()


def _validate_history(history: tuple[FermentationState, ...]) -> None:
    if not history:
        raise ExtractionConstraintError("Alcoholic fermentation history cannot be empty")
    prior = -1.0
    for state in history:
        if state.hour < prior:
            raise ExtractionConstraintError("Fermentation history must be ordered by hour")
        prior = state.hour


def _interval_overlap(start: float, end: float, window_start: float, window_end: float) -> float:
    return max(0.0, min(end, window_end) - max(start, window_start))


def simulate_extraction(
    alcoholic_history: tuple[FermentationState, ...],
    plan: ExtractionPlan = ExtractionPlan(),
    *,
    whole_cluster_fraction: float = 0.0,
    source_extraction_potential: float | None = None,
) -> ExtractionResult:
    """Integrate extraction over the realized alcoholic-fermentation history."""
    _validate_history(alcoholic_history)
    if not 0.0 <= whole_cluster_fraction <= 1.0:
        raise ExtractionConstraintError("whole_cluster_fraction must be within 0..1")
    if source_extraction_potential is not None and not 0.0 <= source_extraction_potential <= 1.0:
        raise ExtractionConstraintError("source_extraction_potential must be within 0..1")

    history_end = alcoholic_history[-1].hour
    contact_end = history_end if plan.maceration_end_hour is None else min(plan.maceration_end_hour, history_end)
    contact_start = min(plan.maceration_start_hour, contact_end)
    site_scale = 1.0 if source_extraction_potential is None else 0.55 + 0.90 * source_extraction_potential

    anthocyanin = 0.0
    tannin = 0.0
    phenolic = 0.0
    contact_hours = 0.0
    used_events: set[int] = set()
    curve: list[ExtractionPoint] = [
        ExtractionPoint(
            hour=alcoholic_history[0].hour,
            anthocyanin_index=0.0,
            tannin_index=0.0,
            phenolic_index=0.0,
        )
    ]

    for left, right in zip(alcoholic_history, alcoholic_history[1:]):
        if right.hour <= left.hour:
            continue
        overlap = _interval_overlap(left.hour, right.hour, contact_start, contact_end)
        if overlap <= 0.0:
            curve.append(
                ExtractionPoint(right.hour, anthocyanin, tannin, phenolic, 0.0)
            )
            continue

        active_start = max(left.hour, contact_start)
        active_end = min(right.hour, contact_end)
        event_load = 0.0
        for index, event in enumerate(plan.cap_management_events):
            # Half-open intervals prevent an event on a step boundary from being
            # applied twice. The final history endpoint is included explicitly.
            in_interval = active_start <= event.hour < active_end
            if active_end == history_end and abs(event.hour - active_end) <= 1e-9:
                in_interval = True
            if in_interval:
                event_load += event.intensity
                used_events.add(index)

        cap_multiplier = 1.0 + 0.35 * min(2.0, event_load)
        midpoint_temp = (left.temp_c + right.temp_c) / 2.0
        midpoint_ethanol = (left.ethanol_pct + right.ethanol_pct) / 2.0
        midpoint_hour = (active_start + active_end) / 2.0

        temp_factor = clamp((midpoint_temp - 10.0) / 20.0)
        ethanol_factor = clamp(midpoint_ethanol / 14.0)
        # Anthocyanin extraction is front-loaded relative to seed/stem tannin.
        early_factor = clamp(1.0 - midpoint_hour / (24.0 * 18.0), 0.10, 1.0)
        late_factor = clamp(midpoint_hour / (24.0 * 18.0), 0.0, 1.0)
        scale = plan.baseline_extraction_scale * site_scale * cap_multiplier

        anth_rate_per_day = 0.018 * scale * (
            0.55 * temp_factor + 0.30 * early_factor + 0.15 * ethanol_factor
        )
        tannin_rate_per_day = 0.009 * scale * (
            0.20 * temp_factor
            + 0.50 * ethanol_factor
            + 0.20 * whole_cluster_fraction
            + 0.10 * late_factor
        )
        phenolic_rate_per_day = 0.011 * scale * (
            0.30 * temp_factor + 0.45 * ethanol_factor + 0.15 * late_factor + 0.10 * whole_cluster_fraction
        )
        days = overlap / 24.0
        anthocyanin = clamp(anthocyanin + anth_rate_per_day * days * (1.0 - anthocyanin))
        tannin = clamp(tannin + tannin_rate_per_day * days * (1.0 - tannin))
        phenolic = clamp(phenolic + phenolic_rate_per_day * days * (1.0 - phenolic))
        contact_hours += overlap
        curve.append(
            ExtractionPoint(
                hour=right.hour,
                anthocyanin_index=anthocyanin,
                tannin_index=tannin,
                phenolic_index=phenolic,
                cap_event_load=event_load,
            )
        )

    press_component = plan.press_wine_blend_fraction * plan.press_severity
    tannin_before_press = tannin
    phenolic_before_press = phenolic
    tannin = clamp(tannin + 0.22 * press_component * (1.0 - tannin))
    phenolic = clamp(phenolic + 0.18 * press_component * (1.0 - phenolic))
    press_tannin_increment = tannin - tannin_before_press
    press_phenolic_increment = phenolic - phenolic_before_press

    warnings: list[str] = []
    ignored = len(plan.cap_management_events) - len(used_events)
    if ignored:
        warnings.append(f"{ignored} cap-management event(s) fell outside the modeled skin-contact window.")
    if plan.press_wine_blend_fraction > 0.0 and plan.press_severity <= 0.0:
        warnings.append("Press wine was blended back with zero modeled press severity; no press extraction increment was applied.")
    if plan.maceration_end_hour is not None and plan.maceration_end_hour > history_end:
        warnings.append("Maceration end extends beyond the available fermentation history; extraction was integrated only through the observed history.")

    return ExtractionResult(
        anthocyanin_index=anthocyanin,
        tannin_index=tannin,
        phenolic_index=phenolic,
        skin_contact_hours=contact_hours,
        cap_event_count=len(used_events),
        ignored_cap_event_count=ignored,
        press_tannin_increment=press_tannin_increment,
        press_phenolic_increment=press_phenolic_increment,
        curve=tuple(curve),
        warnings=tuple(warnings),
    )
