"""Evidence-facing fermentation guidance for the simulation layer.

The low-level fermentation engine contains game-model priors. This module keeps
published operational guidance separate from those priors so that evidence can
inform warnings without turning empirical ranges into false chemical laws.
"""
from __future__ import annotations

from dataclasses import dataclass

from .fermentation_process import FermentationPlan, MustComposition


AWRI_YAN_URL = (
    "https://www.awri.com.au/industry_support/winemaking_resources/"
    "wine_fermentation/yan/"
)
AWRI_TEMPERATURE_URL = (
    "https://www.awri.com.au/industry_support/winemaking_resources/"
    "winemaking-practices/fermentation-temperature/"
)
AWRI_MLF_URL = (
    "https://www.awri.com.au/industry_support/winemaking_resources/"
    "wine_fermentation/mlf-starter-culture/"
)


@dataclass(frozen=True)
class FermentationGuidance:
    status: str
    risk_score: float
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence_urls: tuple[str, ...] = ()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def minimum_low_risk_yan_mg_l(style: str) -> float | None:
    """Return a conservative AWRI-style YAN guide when one maps cleanly.

    AWRI gives approximate low-risk minimums of 150 mg/L for whites and
    100 mg/L for reds. Rosé and sparkling base are mapped to the white guide as
    a conservative simulator policy. Orange wine is left unresolved because its
    skin-contact nitrogen extraction does not map cleanly to either published
    category.
    """
    key = style.strip().casefold()
    if key == "red":
        return 100.0
    if key in {"white", "rosé", "rose", "sparkling_base"}:
        return 150.0
    return None


def assess_alcoholic_fermentation(
    must: MustComposition,
    plan: FermentationPlan,
) -> FermentationGuidance:
    """Assess process risk without declaring a fermentation chemically impossible."""
    issues: list[str] = []
    warnings: list[str] = []
    risk = 0.0

    threshold = minimum_low_risk_yan_mg_l(plan.style)
    if threshold is None:
        warnings.append(
            f"No published style-specific YAN minimum is mapped for {plan.style!r}; "
            "the kinetic engine remains strain- and process-dependent."
        )
    elif must.yan_mg_l < threshold:
        shortfall = (threshold - must.yan_mg_l) / threshold
        risk += 0.45 * _clamp(shortfall)
        issues.append(
            f"Initial YAN {must.yan_mg_l:.0f} mg/L is below the approximate "
            f"{threshold:.0f} mg/L low-risk guide for this simulator style."
        )

    if must.temp_c > 35.0:
        risk += 0.40
        issues.append(
            "Initial must temperature exceeds 35 C; extreme fermentation "
            "temperature can reduce yeast health and increase stuck-ferment risk."
        )
    if plan.alcoholic_params.cooling_setpoint_c is None:
        warnings.append(
            "No active cooling setpoint is configured; exothermic temperature rise "
            "can become important in fast or high-YAN fermentations."
        )
    elif plan.alcoholic_params.cooling_setpoint_c > 35.0:
        risk += 0.25
        issues.append("The configured cooling setpoint is above 35 C.")

    if plan.inoculation_mode.casefold() != "inoculated":
        warnings.append(
            "Published YAN guides depend on yeast strain and fermentation conditions; "
            "native or mixed populations can depart materially from the guide."
        )

    status = "elevated_risk" if issues else "within_general_guides"
    return FermentationGuidance(
        status=status,
        risk_score=_clamp(risk),
        issues=tuple(issues),
        warnings=tuple(warnings),
        evidence_urls=(AWRI_YAN_URL, AWRI_TEMPERATURE_URL),
    )


def assess_malolactic_conditions(
    must: MustComposition,
    plan: FermentationPlan,
    *,
    estimated_alcohol_pct: float | None = None,
    total_so2_mg_l: float | None = None,
) -> FermentationGuidance:
    """Assess MLF conditions against broad AWRI operational ranges.

    This is advisory. Strain tolerance, bound/molecular SO2, yeast-bacteria
    interaction, nutrient state, and other factors can materially change MLF.
    """
    if not plan.malolactic:
        return FermentationGuidance(
            status="not_planned",
            risk_score=0.0,
            evidence_urls=(AWRI_MLF_URL,),
        )

    alcohol = estimated_alcohol_pct
    if alcohol is None:
        fermentable_sugar = max(0.0, must.sugar_g_l - plan.target_residual_sugar_g_l)
        alcohol = (
            must.initial_ethanol_pct
            + fermentable_sugar / plan.alcoholic_params.sugar_g_l_per_abv_pct
        )

    issues: list[str] = []
    warnings: list[str] = []
    risk = 0.0

    if plan.mlf_start_temp_c < 15.0 or plan.mlf_start_temp_c > 25.0:
        risk += 0.30
        issues.append("MLF start temperature is outside the broad 15-25 C guide.")
    elif plan.mlf_start_temp_c < 18.0 or plan.mlf_start_temp_c > 22.0:
        risk += 0.10
        warnings.append("MLF temperature is outside the preferred 18-22 C band.")

    if must.ph <= 3.0:
        risk += 0.30
        issues.append("Wine pH is at or below 3.0, an unfavourable MLF condition.")
    elif must.ph < 3.2:
        risk += 0.10
        warnings.append("Low pH can materially restrict malolactic strain choice.")

    if alcohol >= 16.0:
        risk += 0.35
        issues.append("Estimated alcohol is at or above 16% v/v.")
    elif alcohol >= 15.0:
        risk += 0.20
        warnings.append(
            "Estimated alcohol is at or above 15% v/v; tolerant MLF strains may be required."
        )

    if total_so2_mg_l is None:
        warnings.append(
            "Total SO2 was not supplied. Free SO2 alone is not enough to apply the "
            "published total-SO2 MLF guide."
        )
    elif total_so2_mg_l >= 40.0:
        risk += 0.30
        issues.append("Total SO2 is at or above 40 mg/L, an unfavourable MLF condition.")

    status = "elevated_risk" if issues else "within_general_guides"
    return FermentationGuidance(
        status=status,
        risk_score=_clamp(risk),
        issues=tuple(issues),
        warnings=tuple(warnings),
        evidence_urls=(AWRI_MLF_URL,),
    )


def estimate_sparkling_co2_volumes(
    tirage_sugar_g_l: float,
    *,
    base_wine_co2_volumes: float = 0.0,
) -> float:
    """Estimate traditional-method CO2 volumes from tirage sugar.

    The simulator uses the practical approximation that 24 g/L fermentable
    tirage sugar produces about six gas volumes after complete secondary
    fermentation. This is a planning relation, not a pressure-vessel equation.
    """
    if tirage_sugar_g_l < 0.0 or tirage_sugar_g_l > 60.0:
        raise ValueError("tirage_sugar_g_l must be within 0..60")
    if base_wine_co2_volumes < 0.0 or base_wine_co2_volumes > 5.0:
        raise ValueError("base_wine_co2_volumes must be within 0..5")
    return base_wine_co2_volumes + tirage_sugar_g_l / 4.0
