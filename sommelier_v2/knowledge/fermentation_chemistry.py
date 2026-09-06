"""Chemistry-facing process risk mechanics for fermentation.

This module keeps published operational chemistry separate from hard legal rules
and from the lower-level kinetic priors. The functions here are bounded
simulation transforms. They preserve directional relationships that matter in a
cellar simulation without pretending that one threshold diagnoses a real wine.

Important evidence distinctions used by the model:
- YAN demand depends on yeast, sugar, temperature, aeration and process context.
- Late inorganic nitrogen does not behave like an early growth-phase addition.
- White-juice turbidity has a non-monotonic relationship with fermentation and
  aroma risk; 100 NTU is treated only as a study-informed simulator reference.
- Sulfur-dioxide protection depends strongly on pH because the molecular
  fraction falls as pH rises.
- Rot/botrytis condition and prolonged unsulfured post-fermentation storage are
  risk inputs, not deterministic spoilage diagnoses.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pow


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


NUTRIENT_KINDS = frozenset(
    {
        "organic_or_inorganic_nutrient",
        "dap",
        "inorganic",
        "organic",
        "complex",
        "mixed",
    }
)


@dataclass(frozen=True)
class NutrientTimingEffect:
    progress_index: float
    late_fraction: float
    inorganic_fraction: float
    h2s_relief_index: float
    residual_nitrogen_risk: float
    warning: str | None = None


@dataclass(frozen=True)
class ProcessChemistryAssessment:
    initial_microbiological_risk: float
    juice_solids_risk: float
    nutrient_timing_risk: float
    molecular_so2_mg_l: float | None
    post_fermentation_microbiological_risk: float
    warnings: tuple[str, ...] = ()


def molecular_so2_mg_l(
    free_so2_mg_l: float,
    ph: float,
    *,
    pka: float = 1.81,
) -> float:
    """Estimate molecular SO2 from free SO2 and pH.

    Uses a Henderson-Hasselbalch style approximation with pKa 1.81. Temperature,
    ethanol and matrix effects are not represented, so this is a simulator
    estimate rather than an analytical result.
    """
    if free_so2_mg_l < 0.0:
        raise ValueError("free_so2_mg_l must be non-negative")
    if not 2.0 <= ph <= 5.0:
        raise ValueError("ph must be within 2.0..5.0")
    fraction = 1.0 / (1.0 + pow(10.0, ph - pka))
    return free_so2_mg_l * fraction


def initial_microbiological_risk(
    *,
    ph: float,
    rot_fraction: float,
    botrytis_fraction: float,
    free_so2_mg_l: float,
) -> float:
    """Bounded must-condition risk prior.

    Rot is weighted more strongly than botrytis because the input is intended to
    represent compromised fruit entering the cellar, not noble-rot suitability.
    SO2 receives only a modest protective term because must-level free SO2 is not
    a universal proxy for microbial control.
    """
    high_ph = clamp((ph - 3.35) / 0.85)
    condition = clamp(0.68 * rot_fraction + 0.32 * botrytis_fraction)
    protection = clamp(free_so2_mg_l / 45.0)
    return clamp(0.58 * condition + 0.27 * high_ph - 0.15 * protection)


def white_juice_solids_risk(
    style: str,
    turbidity_ntu: float | None,
    solids_pct: float,
) -> float:
    """Return a bounded white-juice clarification risk prior.

    If measured turbidity is supplied, the curve is lowest near 100 NTU and
    rises at very low or very high turbidity. The reference is not treated as a
    universal target. If turbidity is unavailable, solids percentage contributes
    only a weak fallback prior because percent solids and NTU are not equivalent.
    Red and orange fermentations return zero because their solids context is not
    comparable to clarified white juice.
    """
    key = style.strip().casefold()
    if key not in {"white", "rosé", "rose", "sparkling_base"}:
        return 0.0
    if turbidity_ntu is not None:
        if turbidity_ntu < 0.0:
            raise ValueError("turbidity_ntu must be non-negative")
        low = clamp((55.0 - turbidity_ntu) / 55.0)
        high = clamp((turbidity_ntu - 160.0) / 240.0)
        return clamp(0.55 * low + 0.75 * high)
    return clamp((solids_pct - 4.0) / 16.0) * 0.35


def nutrient_timing_effect(
    *,
    kind: str,
    yan_mg_l: float,
    ethanol_pct: float,
    sugar_g_l: float,
    initial_sugar_g_l: float,
) -> NutrientTimingEffect:
    """Describe the process effect of one nutrient addition.

    The model does not claim a universal DAP cutoff. Instead it uses a smooth
    fermentation-progress index. Late inorganic additions receive less modeled
    H2S relief and a larger residual-nitrogen/spoilage-risk prior.
    """
    key = kind.strip().casefold()
    if key not in NUTRIENT_KINDS:
        raise ValueError(f"Unsupported nutrient kind {kind!r}")
    if yan_mg_l < 0.0:
        raise ValueError("yan_mg_l must be non-negative")

    sugar_progress = 0.0
    if initial_sugar_g_l > 0.0:
        sugar_progress = clamp(1.0 - sugar_g_l / initial_sugar_g_l)
    alcohol_progress = clamp(ethanol_pct / 12.5)
    progress = max(sugar_progress, alcohol_progress)
    late = clamp((progress - 0.42) / 0.48)

    if key in {"dap", "inorganic"}:
        inorganic = 1.0
    elif key == "organic_or_inorganic_nutrient":
        inorganic = 0.50
    elif key == "mixed":
        inorganic = 0.40
    elif key == "complex":
        inorganic = 0.20
    else:
        inorganic = 0.08

    dose = clamp(yan_mg_l / 180.0)
    h2s_relief = clamp(dose * (1.0 - 0.68 * late))
    residual_risk = clamp(dose * late * (0.25 + 0.75 * inorganic))
    warning = None
    if residual_risk >= 0.25:
        warning = (
            f"Late {kind} addition occurs after substantial modeled fermentation "
            "progress; H2S benefit is reduced and residual-nitrogen risk is elevated."
        )
    return NutrientTimingEffect(
        progress_index=progress,
        late_fraction=late,
        inorganic_fraction=inorganic,
        h2s_relief_index=h2s_relief,
        residual_nitrogen_risk=residual_risk,
        warning=warning,
    )


def post_fermentation_microbiological_risk(
    *,
    base_risk: float,
    ph: float,
    free_so2_mg_l: float | None,
    delay_days: float,
    residual_yan_mg_l: float,
    sterile_packaging: bool,
) -> tuple[float, float | None, tuple[str, ...]]:
    """Estimate relative post-fermentation microbial risk.

    About 0.6 mg/L molecular SO2 is used only as a Brett-control guide scale,
    not as a release threshold. Sterile packaging sharply reduces the modeled
    viable-organism pathway but does not erase oxidation or pre-existing faults.
    """
    warnings: list[str] = []
    molecular = None
    protection = 0.0
    if free_so2_mg_l is None:
        warnings.append(
            "No post-fermentation free SO2 target was supplied; pH-dependent "
            "molecular SO2 protection cannot be credited."
        )
    else:
        molecular = molecular_so2_mg_l(free_so2_mg_l, ph)
        protection = clamp(molecular / 0.60)
        if molecular < 0.30:
            warnings.append(
                "Modeled molecular SO2 is below 0.30 mg/L; microbiological "
                "protection is weak in this simulator state."
            )

    high_ph = clamp((ph - 3.45) / 0.75)
    delay = clamp(delay_days / 30.0)
    residual_n = clamp(residual_yan_mg_l / 220.0)
    risk = clamp(
        0.38 * clamp(base_risk)
        + 0.22 * high_ph
        + 0.24 * delay
        + 0.16 * residual_n
        - 0.42 * protection
    )
    if sterile_packaging:
        risk *= 0.18
    if delay_days >= 14.0:
        warnings.append(
            "Extended unsulfured or under-protected post-fermentation storage "
            "increases the modeled Brett/VA risk window."
        )
    return clamp(risk), molecular, tuple(warnings)


def assess_process_chemistry(
    *,
    style: str,
    ph: float,
    free_so2_mg_l: float,
    post_fermentation_free_so2_mg_l: float | None,
    post_fermentation_so2_delay_days: float,
    final_yan_mg_l: float,
    rot_fraction: float,
    botrytis_fraction: float,
    solids_pct: float,
    juice_turbidity_ntu: float | None,
    nutrient_timing_risk: float,
    sterile_packaging: bool,
) -> ProcessChemistryAssessment:
    initial = initial_microbiological_risk(
        ph=ph,
        rot_fraction=rot_fraction,
        botrytis_fraction=botrytis_fraction,
        free_so2_mg_l=free_so2_mg_l,
    )
    solids = white_juice_solids_risk(style, juice_turbidity_ntu, solids_pct)
    base = clamp(initial + 0.24 * solids + 0.28 * nutrient_timing_risk)
    post, molecular, post_warnings = post_fermentation_microbiological_risk(
        base_risk=base,
        ph=ph,
        free_so2_mg_l=post_fermentation_free_so2_mg_l,
        delay_days=post_fermentation_so2_delay_days,
        residual_yan_mg_l=final_yan_mg_l,
        sterile_packaging=sterile_packaging,
    )
    warnings: list[str] = list(post_warnings)
    if initial >= 0.55:
        warnings.append("Compromised fruit condition creates elevated modeled microbial risk at crush.")
    if solids >= 0.50:
        warnings.append("White-juice clarification state is outside the lower-risk part of the simulator curve.")
    if nutrient_timing_risk >= 0.35:
        warnings.append("Nutrient timing creates elevated residual-nitrogen/process risk.")
    return ProcessChemistryAssessment(
        initial_microbiological_risk=initial,
        juice_solids_risk=solids,
        nutrient_timing_risk=clamp(nutrient_timing_risk),
        molecular_so2_mg_l=molecular,
        post_fermentation_microbiological_risk=post,
        warnings=tuple(warnings),
    )
