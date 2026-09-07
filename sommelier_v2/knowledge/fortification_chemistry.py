"""Physical mass balance for wine fortification.

A fermentation arrest labelled ``fortification`` is process intent, not a
physical alcohol addition. This module performs the separate liquid operation.
It conserves ethanol-equivalent volume and explicitly measured solute mass while
keeping ideal additive-volume planning distinct from measured final volume.

Ethanol/water mixtures can contract on mixing. Therefore ``base volume + spirit
volume`` is exposed only as an ideal additive-volume basis. Exact finished
concentrations require an explicit measured final volume. Reactive/nonlinear
properties such as pH, free SO2 and titratable acidity are never averaged from
source liquids; they require a post-mix measurement.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real


class FortificationConstraintError(ValueError):
    """Raised when a fortification request is physically invalid."""


def _real(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise FortificationConstraintError(
            f"{name} must be a real numeric value; got {value!r}"
        )
    number = float(value)
    if not isfinite(number):
        raise FortificationConstraintError(f"{name} must be finite; got {value!r}")
    return number


def _bounded(name: str, value: float | None, low: float, high: float) -> None:
    if value is None:
        return
    number = _real(name, value)
    if number < low or number > high:
        raise FortificationConstraintError(
            f"{name} must be within {low}..{high}; got {number}"
        )


@dataclass(frozen=True)
class FortificationLiquid:
    """One liquid entering a fortification operation.

    Residual sugar is mandatory so the operation cannot silently treat a spirit
    or sweetening liquid as sugar-free. Other solutes may remain unknown.
    """

    source_id: str
    volume_l: float
    ethanol_pct: float
    residual_sugar_g_l: float
    malic_acid_g_l: float | None = None
    lactic_acid_g_l: float | None = None
    tartaric_acid_g_l: float | None = None
    volatile_acidity_g_l: float | None = None
    total_so2_mg_l: float | None = None
    ph: float | None = None
    free_so2_mg_l: float | None = None
    titratable_acidity_g_l: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise FortificationConstraintError("Fortification liquid source_id is required.")
        volume = _real("volume_l", self.volume_l)
        if volume <= 0 or volume > 10_000_000:
            raise FortificationConstraintError(
                f"volume_l must be >0 and <=10000000; got {volume}"
            )
        _bounded("ethanol_pct", self.ethanol_pct, 0.0, 100.0)
        _bounded("residual_sugar_g_l", self.residual_sugar_g_l, 0.0, 2000.0)
        _bounded("malic_acid_g_l", self.malic_acid_g_l, 0.0, 50.0)
        _bounded("lactic_acid_g_l", self.lactic_acid_g_l, 0.0, 50.0)
        _bounded("tartaric_acid_g_l", self.tartaric_acid_g_l, 0.0, 50.0)
        _bounded("volatile_acidity_g_l", self.volatile_acidity_g_l, 0.0, 20.0)
        _bounded("total_so2_mg_l", self.total_so2_mg_l, 0.0, 2000.0)
        _bounded("ph", self.ph, 1.5, 7.0)
        _bounded("free_so2_mg_l", self.free_so2_mg_l, 0.0, 1000.0)
        _bounded("titratable_acidity_g_l", self.titratable_acidity_g_l, 0.0, 100.0)


@dataclass(frozen=True)
class FortificationPostMixMeasurements:
    """Finished-liquid measurements that cannot be derived safely by averaging."""

    final_volume_l: float | None = None
    ph: float | None = None
    free_so2_mg_l: float | None = None
    titratable_acidity_g_l: float | None = None

    def __post_init__(self) -> None:
        if self.final_volume_l is not None:
            volume = _real("final_volume_l", self.final_volume_l)
            if volume <= 0 or volume > 20_000_000:
                raise FortificationConstraintError(
                    f"final_volume_l must be >0 and <=20000000; got {volume}"
                )
        _bounded("post_mix.ph", self.ph, 1.5, 7.0)
        _bounded("post_mix.free_so2_mg_l", self.free_so2_mg_l, 0.0, 1000.0)
        _bounded(
            "post_mix.titratable_acidity_g_l",
            self.titratable_acidity_g_l,
            0.0,
            100.0,
        )


@dataclass(frozen=True)
class FortificationResult:
    base_source_id: str
    spirit_source_id: str
    base_volume_l: float
    spirit_volume_l: float
    ideal_additive_volume_l: float
    measured_final_volume_l: float | None
    volume_delta_l: float | None

    ethanol_equivalent_l: float
    ideal_additive_ethanol_pct: float
    volume_corrected_ethanol_pct: float | None

    residual_sugar_g: float
    ideal_additive_residual_sugar_g_l: float
    volume_corrected_residual_sugar_g_l: float | None

    malic_acid_g: float | None
    ideal_additive_malic_acid_g_l: float | None
    volume_corrected_malic_acid_g_l: float | None
    lactic_acid_g: float | None
    ideal_additive_lactic_acid_g_l: float | None
    volume_corrected_lactic_acid_g_l: float | None
    tartaric_acid_g: float | None
    ideal_additive_tartaric_acid_g_l: float | None
    volume_corrected_tartaric_acid_g_l: float | None
    volatile_acidity_g: float | None
    ideal_additive_volatile_acidity_g_l: float | None
    volume_corrected_volatile_acidity_g_l: float | None
    input_total_so2_mg: float | None
    ideal_additive_total_so2_mg_l: float | None
    volume_corrected_total_so2_mg_l: float | None

    ph: float | None
    free_so2_mg_l: float | None
    titratable_acidity_g_l: float | None
    unresolved_fields: tuple[str, ...]
    warnings: tuple[str, ...]


def _solute_balance(
    base: FortificationLiquid,
    spirit: FortificationLiquid,
    field: str,
    additive_volume_l: float,
    measured_volume_l: float | None,
) -> tuple[float | None, float | None, float | None]:
    base_value = getattr(base, field)
    spirit_value = getattr(spirit, field)
    if base_value is None or spirit_value is None:
        return None, None, None
    total = base.volume_l * float(base_value) + spirit.volume_l * float(spirit_value)
    additive_concentration = total / additive_volume_l
    measured_concentration = (
        total / measured_volume_l if measured_volume_l is not None else None
    )
    return total, additive_concentration, measured_concentration


def ideal_spirit_volume_for_target_abv(
    *,
    base_volume_l: float,
    base_ethanol_pct: float,
    spirit_ethanol_pct: float,
    target_ethanol_pct: float,
) -> float:
    """Solve spirit volume on an explicitly ideal additive-volume basis.

    This is a planning relation, not a guarantee of the measured finished ABV,
    because the final liquid volume can differ from the arithmetic volume sum.
    """

    base_volume = _real("base_volume_l", base_volume_l)
    base_abv = _real("base_ethanol_pct", base_ethanol_pct)
    spirit_abv = _real("spirit_ethanol_pct", spirit_ethanol_pct)
    target = _real("target_ethanol_pct", target_ethanol_pct)
    if base_volume <= 0:
        raise FortificationConstraintError("base_volume_l must be positive.")
    for name, value in (
        ("base_ethanol_pct", base_abv),
        ("spirit_ethanol_pct", spirit_abv),
        ("target_ethanol_pct", target),
    ):
        if value < 0 or value > 100:
            raise FortificationConstraintError(f"{name} must be within 0..100.")
    if target == base_abv:
        return 0.0
    if not base_abv < target < spirit_abv:
        raise FortificationConstraintError(
            "A positive fortifying-spirit addition requires base ABV < target ABV < spirit ABV."
        )
    return base_volume * (target - base_abv) / (spirit_abv - target)


def fortify_liquid(
    base: FortificationLiquid,
    spirit: FortificationLiquid,
    *,
    post_mix: FortificationPostMixMeasurements | None = None,
) -> FortificationResult:
    """Apply one physical spirit addition with explicit volume-basis semantics."""

    if base.source_id == spirit.source_id:
        raise FortificationConstraintError(
            "Base wine and fortifying spirit must have distinct source identities."
        )
    if spirit.ethanol_pct <= base.ethanol_pct:
        raise FortificationConstraintError(
            "Fortifying spirit ABV must exceed the base liquid ABV."
        )

    additive_volume = base.volume_l + spirit.volume_l
    ethanol_l = (
        base.volume_l * base.ethanol_pct / 100.0
        + spirit.volume_l * spirit.ethanol_pct / 100.0
    )
    ideal_abv = ethanol_l / additive_volume * 100.0

    sugar_g = (
        base.volume_l * base.residual_sugar_g_l
        + spirit.volume_l * spirit.residual_sugar_g_l
    )
    ideal_sugar = sugar_g / additive_volume

    measurement = post_mix or FortificationPostMixMeasurements()
    measured_volume = measurement.final_volume_l
    volume_delta = (
        measured_volume - additive_volume if measured_volume is not None else None
    )
    corrected_abv = ethanol_l / measured_volume * 100.0 if measured_volume else None
    corrected_sugar = sugar_g / measured_volume if measured_volume else None
    if corrected_abv is not None and corrected_abv > 100.0 + 1e-9:
        raise FortificationConstraintError(
            "Measured final volume is incompatible with conserved ethanol-equivalent volume."
        )

    balances = {
        field: _solute_balance(base, spirit, field, additive_volume, measured_volume)
        for field in (
            "malic_acid_g_l",
            "lactic_acid_g_l",
            "tartaric_acid_g_l",
            "volatile_acidity_g_l",
            "total_so2_mg_l",
        )
    }

    unresolved: list[str] = []
    warnings: list[str] = []
    if measured_volume is None:
        unresolved.append("measured_final_volume_l")
        warnings.append(
            "Final volume is unmeasured; ABV and concentrations are available only on an ideal additive-volume planning basis."
        )
    elif abs(volume_delta or 0.0) > 1e-9:
        warnings.append(
            "Measured final volume differs from arithmetic input volume; volume-corrected concentrations use the measured final volume."
        )

    for field in (
        "malic_acid_g_l",
        "lactic_acid_g_l",
        "tartaric_acid_g_l",
        "volatile_acidity_g_l",
        "total_so2_mg_l",
    ):
        if balances[field][0] is None:
            unresolved.append(field)

    for field in ("ph", "free_so2_mg_l", "titratable_acidity_g_l"):
        if getattr(measurement, field) is None:
            unresolved.append(field)
            if getattr(base, field) is not None and getattr(spirit, field) is not None:
                warnings.append(
                    f"Source {field} values are complete but are not averaged; a post-fortification measurement is required."
                )

    malic_g, malic_ideal, malic_corrected = balances["malic_acid_g_l"]
    lactic_g, lactic_ideal, lactic_corrected = balances["lactic_acid_g_l"]
    tartaric_g, tartaric_ideal, tartaric_corrected = balances["tartaric_acid_g_l"]
    va_g, va_ideal, va_corrected = balances["volatile_acidity_g_l"]
    so2_mg, so2_ideal, so2_corrected = balances["total_so2_mg_l"]

    return FortificationResult(
        base_source_id=base.source_id,
        spirit_source_id=spirit.source_id,
        base_volume_l=base.volume_l,
        spirit_volume_l=spirit.volume_l,
        ideal_additive_volume_l=additive_volume,
        measured_final_volume_l=measured_volume,
        volume_delta_l=volume_delta,
        ethanol_equivalent_l=ethanol_l,
        ideal_additive_ethanol_pct=ideal_abv,
        volume_corrected_ethanol_pct=corrected_abv,
        residual_sugar_g=sugar_g,
        ideal_additive_residual_sugar_g_l=ideal_sugar,
        volume_corrected_residual_sugar_g_l=corrected_sugar,
        malic_acid_g=malic_g,
        ideal_additive_malic_acid_g_l=malic_ideal,
        volume_corrected_malic_acid_g_l=malic_corrected,
        lactic_acid_g=lactic_g,
        ideal_additive_lactic_acid_g_l=lactic_ideal,
        volume_corrected_lactic_acid_g_l=lactic_corrected,
        tartaric_acid_g=tartaric_g,
        ideal_additive_tartaric_acid_g_l=tartaric_ideal,
        volume_corrected_tartaric_acid_g_l=tartaric_corrected,
        volatile_acidity_g=va_g,
        ideal_additive_volatile_acidity_g_l=va_ideal,
        volume_corrected_volatile_acidity_g_l=va_corrected,
        input_total_so2_mg=so2_mg,
        ideal_additive_total_so2_mg_l=so2_ideal,
        volume_corrected_total_so2_mg_l=so2_corrected,
        ph=measurement.ph,
        free_so2_mg_l=measurement.free_so2_mg_l,
        titratable_acidity_g_l=measurement.titratable_acidity_g_l,
        unresolved_fields=tuple(dict.fromkeys(unresolved)),
        warnings=tuple(warnings),
    )
