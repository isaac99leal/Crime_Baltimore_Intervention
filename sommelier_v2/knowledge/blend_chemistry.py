"""Physical chemistry accounting for winery blends.

This module deliberately separates quantities that can be conserved by an
instantaneous volume-weighted mass balance from quantities that cannot safely be
inferred by averaging labels or measurements from the source wines.

The blend volume is the sum of explicit source draws. Provenance-level transfer
losses belong in :mod:`winery_provenance`; this module describes the chemistry of
the wine that actually enters one blend operation.

Linear mass accounting is allowed for ethanol and explicitly measured solutes.
Nonlinear/reactive finished-wine properties such as pH, free SO2 and titratable
acidity require a post-mix measurement. Dissolved oxygen is only modeled when the
operation-level oxygen delta is explicit; ``None`` never means zero pickup.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real


class BlendChemistryConstraintError(ValueError):
    """Raised when a blend chemistry input is impossible or under-specified."""


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise BlendChemistryConstraintError(
            f"{name} must be a real numeric value; got {value!r}"
        )
    number = float(value)
    if not isfinite(number):
        raise BlendChemistryConstraintError(f"{name} must be finite; got {value!r}")
    return number


def _bounded(name: str, value: float | None, low: float, high: float) -> None:
    if value is None:
        return
    number = _finite(name, value)
    if number < low or number > high:
        raise BlendChemistryConstraintError(
            f"{name} must be within {low}..{high}; got {number}"
        )


@dataclass(frozen=True)
class BlendChemistryComponent:
    """Chemistry attached to one explicit source-lot draw.

    Optional means unknown, not zero. Source pH/free-SO2/TA values are accepted as
    observations for provenance and diagnostics, but are never averaged into the
    finished blend.
    """

    source_id: str
    draw_l: float
    ethanol_pct: float | None = None
    residual_sugar_g_l: float | None = None
    malic_acid_g_l: float | None = None
    lactic_acid_g_l: float | None = None
    tartaric_acid_g_l: float | None = None
    volatile_acidity_g_l: float | None = None
    total_so2_mg_l: float | None = None
    dissolved_oxygen_mg_l: float | None = None
    ph: float | None = None
    free_so2_mg_l: float | None = None
    titratable_acidity_g_l: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise BlendChemistryConstraintError("Blend source_id is required.")
        draw = _finite("draw_l", self.draw_l)
        if draw <= 0 or draw > 10_000_000:
            raise BlendChemistryConstraintError(
                f"draw_l must be >0 and <=10000000; got {draw}"
            )
        _bounded("ethanol_pct", self.ethanol_pct, 0.0, 30.0)
        _bounded("residual_sugar_g_l", self.residual_sugar_g_l, 0.0, 700.0)
        _bounded("malic_acid_g_l", self.malic_acid_g_l, 0.0, 30.0)
        _bounded("lactic_acid_g_l", self.lactic_acid_g_l, 0.0, 30.0)
        _bounded("tartaric_acid_g_l", self.tartaric_acid_g_l, 0.0, 30.0)
        _bounded("volatile_acidity_g_l", self.volatile_acidity_g_l, 0.0, 10.0)
        _bounded("total_so2_mg_l", self.total_so2_mg_l, 0.0, 1000.0)
        _bounded("dissolved_oxygen_mg_l", self.dissolved_oxygen_mg_l, 0.0, 30.0)
        _bounded("ph", self.ph, 2.0, 5.0)
        _bounded("free_so2_mg_l", self.free_so2_mg_l, 0.0, 500.0)
        _bounded("titratable_acidity_g_l", self.titratable_acidity_g_l, 0.0, 40.0)


@dataclass(frozen=True)
class BlendPostMixMeasurements:
    """Measurements made on the physically mixed wine.

    These values are observations, not quantities inferred from component labels.
    """

    ph: float | None = None
    free_so2_mg_l: float | None = None
    titratable_acidity_g_l: float | None = None
    total_so2_mg_l: float | None = None
    dissolved_oxygen_mg_l: float | None = None

    def __post_init__(self) -> None:
        _bounded("post_mix.ph", self.ph, 2.0, 5.0)
        _bounded("post_mix.free_so2_mg_l", self.free_so2_mg_l, 0.0, 500.0)
        _bounded(
            "post_mix.titratable_acidity_g_l",
            self.titratable_acidity_g_l,
            0.0,
            40.0,
        )
        _bounded("post_mix.total_so2_mg_l", self.total_so2_mg_l, 0.0, 1000.0)
        _bounded(
            "post_mix.dissolved_oxygen_mg_l",
            self.dissolved_oxygen_mg_l,
            0.0,
            30.0,
        )


@dataclass(frozen=True)
class BlendChemistryResult:
    source_ids: tuple[str, ...]
    volume_l: float

    # Exact ideal-mixing mass balances when every component supplies the field.
    ethanol_l: float | None
    ethanol_pct: float | None
    residual_sugar_g: float | None
    residual_sugar_g_l: float | None
    malic_acid_g: float | None
    malic_acid_g_l: float | None
    lactic_acid_g: float | None
    lactic_acid_g_l: float | None
    tartaric_acid_g: float | None
    tartaric_acid_g_l: float | None
    volatile_acidity_g: float | None
    volatile_acidity_g_l: float | None

    # Total SO2 can be mass-accounted at the instant of mixing, but subsequent
    # binding/oxidation can change the analytical result. Keep this pre-reaction
    # value separate from an optional post-mix measurement.
    input_total_so2_mg: float | None
    pre_reaction_total_so2_mg_l: float | None
    measured_total_so2_mg_l: float | None

    # Reactive/nonlinear properties are measurement-only finished values.
    ph: float | None
    free_so2_mg_l: float | None
    titratable_acidity_g_l: float | None

    # Oxygen is modeled only when source DO is complete and the operation delta
    # is explicit. A post-mix measurement, if supplied, is the authoritative value.
    modeled_dissolved_oxygen_mg_l: float | None
    dissolved_oxygen_mg_l: float | None
    oxygen_model_complete: bool

    conserved_fields: tuple[str, ...]
    measured_fields: tuple[str, ...]
    unresolved_fields: tuple[str, ...]
    warnings: tuple[str, ...]


def _linear_mix(
    components: tuple[BlendChemistryComponent, ...],
    field: str,
    volume_l: float,
) -> tuple[float | None, float | None]:
    values = [getattr(row, field) for row in components]
    if any(value is None for value in values):
        return None, None
    total = sum(row.draw_l * float(value) for row, value in zip(components, values))
    return total, total / volume_l


def blend_chemistry(
    components: tuple[BlendChemistryComponent, ...],
    *,
    post_mix: BlendPostMixMeasurements | None = None,
    operation_oxygen_delta_mg: float | None = None,
) -> BlendChemistryResult:
    """Mass-balance an instantaneous blend without inventing nonlinear chemistry.

    ``operation_oxygen_delta_mg`` is an absolute operation-level oxygen change.
    Positive values are pickup; negative values are modeled oxygen removal or
    consumption. It must be supplied explicitly, including explicit ``0.0``, for
    source dissolved oxygen to become a modeled finished concentration.
    """

    if not components:
        raise BlendChemistryConstraintError("At least one blend component is required.")
    rows = tuple(components)
    source_ids = tuple(row.source_id for row in rows)
    if len(set(source_ids)) != len(source_ids):
        raise BlendChemistryConstraintError(
            "Each source lot may appear only once in one chemistry blend; aggregate its draw first."
        )
    volume_l = sum(row.draw_l for row in rows)
    if not isfinite(volume_l) or volume_l <= 0:
        raise BlendChemistryConstraintError("Blend volume must be finite and positive.")

    conserved: list[str] = []
    unresolved: list[str] = []
    warnings: list[str] = []

    ethanol_values = [row.ethanol_pct for row in rows]
    if any(value is None for value in ethanol_values):
        ethanol_l = None
        ethanol_pct = None
        unresolved.append("ethanol_pct")
    else:
        ethanol_l = sum(
            row.draw_l * float(value) / 100.0
            for row, value in zip(rows, ethanol_values)
        )
        ethanol_pct = (ethanol_l / volume_l) * 100.0
        conserved.append("ethanol")

    linear_results: dict[str, tuple[float | None, float | None]] = {}
    for field in (
        "residual_sugar_g_l",
        "malic_acid_g_l",
        "lactic_acid_g_l",
        "tartaric_acid_g_l",
        "volatile_acidity_g_l",
        "total_so2_mg_l",
    ):
        linear_results[field] = _linear_mix(rows, field, volume_l)
        if linear_results[field][0] is None:
            unresolved.append(field)
        else:
            conserved.append(field)

    sugar_g, sugar_g_l = linear_results["residual_sugar_g_l"]
    malic_g, malic_g_l = linear_results["malic_acid_g_l"]
    lactic_g, lactic_g_l = linear_results["lactic_acid_g_l"]
    tartaric_g, tartaric_g_l = linear_results["tartaric_acid_g_l"]
    va_g, va_g_l = linear_results["volatile_acidity_g_l"]
    total_so2_mg, pre_reaction_total_so2_mg_l = linear_results["total_so2_mg_l"]

    measurement = post_mix or BlendPostMixMeasurements()
    measured_fields = tuple(
        name
        for name, value in (
            ("ph", measurement.ph),
            ("free_so2_mg_l", measurement.free_so2_mg_l),
            ("titratable_acidity_g_l", measurement.titratable_acidity_g_l),
            ("total_so2_mg_l", measurement.total_so2_mg_l),
            ("dissolved_oxygen_mg_l", measurement.dissolved_oxygen_mg_l),
        )
        if value is not None
    )

    for field in ("ph", "free_so2_mg_l", "titratable_acidity_g_l"):
        if getattr(measurement, field) is None:
            unresolved.append(field)
            if all(getattr(row, field) is not None for row in rows):
                warnings.append(
                    f"Source {field} values are complete but are not volume-averaged; a post-mix measurement is required."
                )

    source_do = [row.dissolved_oxygen_mg_l for row in rows]
    modeled_do: float | None = None
    oxygen_complete = False
    if all(value is not None for value in source_do) and operation_oxygen_delta_mg is not None:
        oxygen_delta = _finite("operation_oxygen_delta_mg", operation_oxygen_delta_mg)
        input_oxygen_mg = sum(
            row.draw_l * float(value) for row, value in zip(rows, source_do)
        )
        final_oxygen_mg = input_oxygen_mg + oxygen_delta
        if final_oxygen_mg < -1e-9:
            raise BlendChemistryConstraintError(
                "operation_oxygen_delta_mg removes more oxygen than is present in the source draws."
            )
        modeled_do = max(0.0, final_oxygen_mg) / volume_l
        oxygen_complete = True
    else:
        unresolved.append("dissolved_oxygen_mg_l")
        if all(value is not None for value in source_do) and operation_oxygen_delta_mg is None:
            warnings.append(
                "Source dissolved oxygen is complete but blend-operation oxygen pickup/removal is unknown; DO remains unresolved."
            )

    finished_do = measurement.dissolved_oxygen_mg_l
    if finished_do is None:
        finished_do = modeled_do
    elif modeled_do is not None and abs(finished_do - modeled_do) > 0.25:
        warnings.append(
            "Measured post-mix dissolved oxygen differs materially from the explicit oxygen mass-balance model; the measurement is authoritative."
        )

    if measurement.total_so2_mg_l is None and pre_reaction_total_so2_mg_l is not None:
        warnings.append(
            "Total SO2 is mass-balanced only as a pre-reaction mixing quantity; use a post-mix measurement for finished analytical SO2."
        )

    # De-duplicate while preserving deterministic first occurrence order.
    unresolved_tuple = tuple(dict.fromkeys(unresolved))

    return BlendChemistryResult(
        source_ids=source_ids,
        volume_l=volume_l,
        ethanol_l=ethanol_l,
        ethanol_pct=ethanol_pct,
        residual_sugar_g=sugar_g,
        residual_sugar_g_l=sugar_g_l,
        malic_acid_g=malic_g,
        malic_acid_g_l=malic_g_l,
        lactic_acid_g=lactic_g,
        lactic_acid_g_l=lactic_g_l,
        tartaric_acid_g=tartaric_g,
        tartaric_acid_g_l=tartaric_g_l,
        volatile_acidity_g=va_g,
        volatile_acidity_g_l=va_g_l,
        input_total_so2_mg=total_so2_mg,
        pre_reaction_total_so2_mg_l=pre_reaction_total_so2_mg_l,
        measured_total_so2_mg_l=measurement.total_so2_mg_l,
        ph=measurement.ph,
        free_so2_mg_l=measurement.free_so2_mg_l,
        titratable_acidity_g_l=measurement.titratable_acidity_g_l,
        modeled_dissolved_oxygen_mg_l=modeled_do,
        dissolved_oxygen_mg_l=finished_do,
        oxygen_model_complete=oxygen_complete,
        conserved_fields=tuple(conserved),
        measured_fields=measured_fields,
        unresolved_fields=unresolved_tuple,
        warnings=tuple(warnings),
    )
