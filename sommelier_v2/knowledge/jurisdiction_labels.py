"""Jurisdiction-specific wine-label integrity rules for U.S., Australia and New Zealand.

These rules validate provenance percentages. They are intentionally separate
from EU PDO/PGI production specifications because AVA/GI systems in these
jurisdictions generally regulate label-origin integrity rather than
appellation-specific authorized-grape lists.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .catalog import normalize_name

SOURCES = {
    "us_ttb_appellations": "https://www.ttb.gov/wine/appellations-of-origin",
    "us_ttb_varieties": "https://www.ttb.gov/wine/grape-variety-designations-on-american-wine-labels",
    "us_ttb_vintage": "https://www.ttb.gov/wine/labeling-bam-vintage-date",
    "au_regulations": "https://www.legislation.gov.au/F2018L00286/latest/text",
    "nz_mpi_labelling": "https://www.mpi.govt.nz/food-business/winemaking/labelling-requirements-for-wine-and-wine-products",
    "nz_iponz_gi": "https://www.iponz.govt.nz/get-ip/wine-and-spirit-geographical-indications/use-a-registered-geographical-indication/",
}


@dataclass(frozen=True)
class BlendComponent:
    """One provenance-homogeneous share of a finished wine."""

    volume_pct: float
    grape: str
    country: str
    origins: tuple[str, ...] = ()
    vintage: int | None = None


@dataclass(frozen=True)
class LabelClaims:
    jurisdiction: str
    origin_names: tuple[str, ...] = ()
    origin_type: str | None = None
    variety_names: tuple[str, ...] = ()
    vintage_years: tuple[int, ...] = ()
    shown_variety_percentages: bool = False
    shown_origin_percentages: bool = False
    fully_finished_in_required_area: bool | None = None
    us_varietal_exception_51: bool = False
    us_required_51_statement: bool = False
    registered_nz_gi: bool = False
    country_proportions_shown: bool = False


@dataclass(frozen=True)
class LabelClaimDecision:
    eligible: bool
    status: str
    issues: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def require(self) -> "LabelClaimDecision":
        if not self.eligible:
            raise ValueError("; ".join(self.issues) or self.status)
        return self


def _norm(value: str) -> str:
    return normalize_name(value)


def _component_origin_matches(component: BlendComponent, claim: str) -> bool:
    key = _norm(claim)
    return any(_norm(origin) == key for origin in component.origins) or _norm(component.country) == key


def _sum_origin(components: Sequence[BlendComponent], name: str) -> float:
    return sum(c.volume_pct for c in components if _component_origin_matches(c, name))


def _sum_grape(components: Sequence[BlendComponent], name: str) -> float:
    key = _norm(name)
    return sum(c.volume_pct for c in components if _norm(c.grape) == key)


def _sum_vintage(components: Sequence[BlendComponent], year: int) -> float:
    return sum(c.volume_pct for c in components if c.vintage == year)


def _shares_for_names(
    components: Sequence[BlendComponent],
    names: Iterable[str],
    getter,
) -> list[tuple[str, float]]:
    return [(str(name), getter(components, name)) for name in names]


def _descending(shares: Sequence[tuple[object, float]]) -> bool:
    return all(shares[i][1] + 1e-9 >= shares[i + 1][1] for i in range(len(shares) - 1))


def _validate_components(components: Sequence[BlendComponent]) -> list[str]:
    issues: list[str] = []
    if not components:
        return ["At least one provenance component is required."]
    total = sum(c.volume_pct for c in components)
    if abs(total - 100.0) > 0.25:
        issues.append(f"Component percentages must sum to 100 (got {total:.2f}).")
    for component in components:
        if component.volume_pct <= 0 or component.volume_pct > 100:
            issues.append("Each component percentage must be >0 and <=100.")
        if not component.grape.strip() or not component.country.strip():
            issues.append("Each component requires grape and country provenance.")
    return issues


class JurisdictionLabelValidator:
    """Validate a label claim against provenance-homogeneous blend components."""

    def validate(
        self,
        components: Sequence[BlendComponent],
        claims: LabelClaims,
    ) -> LabelClaimDecision:
        issues = _validate_components(components)
        if issues:
            return LabelClaimDecision(False, "invalid_provenance_components", tuple(issues))
        jurisdiction = _norm(claims.jurisdiction)
        if jurisdiction in {_norm("US"), _norm("USA"), _norm("United States")}:
            return self._validate_us(components, claims)
        if jurisdiction in {_norm("AU"), _norm("Australia")}:
            return self._validate_au(components, claims)
        if jurisdiction in {_norm("NZ"), _norm("New Zealand")}:
            return self._validate_nz(components, claims)
        return LabelClaimDecision(
            False,
            "unsupported_jurisdiction",
            (f"No label-integrity rules are implemented for {claims.jurisdiction}.",),
        )

    def _validate_us(
        self, components: Sequence[BlendComponent], claims: LabelClaims
    ) -> LabelClaimDecision:
        issues: list[str] = []
        evidence = (
            "source:us_ttb_appellations",
            "source:us_ttb_varieties",
            "source:us_ttb_vintage",
        )
        origin_type = _norm(claims.origin_type or "")
        origin_names = claims.origin_names

        if (claims.variety_names or claims.vintage_years) and not origin_names:
            issues.append("A U.S. varietal or vintage claim requires an appellation of origin.")

        if origin_names:
            if origin_type in {_norm("ava"), _norm("american viticultural area")}:
                if len(origin_names) != 1 or _sum_origin(components, origin_names[0]) + 1e-9 < 85:
                    issues.append("An AVA claim requires at least 85% from the named AVA.")
                if claims.fully_finished_in_required_area is not True:
                    issues.append("AVA wine must be fully finished in a state containing the AVA.")
            elif origin_type in {_norm("state"), _norm("county"), _norm("us"), _norm("country")}:
                if len(origin_names) != 1 or _sum_origin(components, origin_names[0]) + 1e-9 < 75:
                    issues.append("This U.S. appellation type requires at least 75% from the named origin.")
                if claims.fully_finished_in_required_area is not True:
                    issues.append("The applicable U.S. finishing requirement is not satisfied.")
            elif origin_type in {_norm("multistate"), _norm("multi state"), _norm("multicounty"), _norm("multi county")}:
                if len(origin_names) not in {2, 3}:
                    issues.append("A multi-state/county appellation must name two or three origins.")
                combined = sum(c.volume_pct for c in components if any(_component_origin_matches(c, n) for n in origin_names))
                if combined < 99.75:
                    issues.append("A multi-state/county appellation requires 100% from the named origins.")
                if not claims.shown_origin_percentages:
                    issues.append("The percentage from each named state/county must be shown.")
            else:
                issues.append(f"Unsupported U.S. origin type {claims.origin_type!r}.")

        if claims.variety_names:
            if len(claims.variety_names) == 1:
                variety = claims.variety_names[0]
                threshold = 51.0 if claims.us_varietal_exception_51 else 75.0
                if claims.us_varietal_exception_51 and not claims.us_required_51_statement:
                    issues.append("The 51% strongly-flavored/labrusca exception requires its label statement.")
                if _sum_grape(components, variety) + 1e-9 < threshold:
                    issues.append(f"Single-variety claim requires at least {threshold:g}% {variety}.")
                if origin_names:
                    qualifying = sum(
                        c.volume_pct
                        for c in components
                        if _norm(c.grape) == _norm(variety)
                        and any(_component_origin_matches(c, n) for n in origin_names)
                    )
                    if qualifying + 1e-9 < threshold:
                        issues.append(
                            f"At least {threshold:g}% of the wine must be both {variety} and from the labeled appellation."
                        )
            else:
                named = {_norm(name) for name in claims.variety_names}
                actual = {_norm(c.grape) for c in components}
                if not actual.issubset(named):
                    issues.append("A multiple-variety U.S. label must name every grape used.")
                if not claims.shown_variety_percentages:
                    issues.append("A multiple-variety U.S. label must show each varietal percentage.")

        if claims.vintage_years:
            if len(claims.vintage_years) != 1:
                issues.append("U.S. vintage-date validation expects one labeled vintage year.")
            elif origin_type in {_norm("us"), _norm("country")}:
                issues.append("A U.S.-country-only appellation does not qualify for a vintage-date claim.")
            else:
                threshold = 95.0 if origin_type in {_norm("ava"), _norm("american viticultural area")} else 85.0
                if _sum_vintage(components, claims.vintage_years[0]) + 1e-9 < threshold:
                    issues.append(
                        f"This U.S. vintage claim requires at least {threshold:g}% from the labeled year."
                    )

        return LabelClaimDecision(
            not issues,
            "us_label_claim_eligible" if not issues else "us_label_claim_violation",
            tuple(issues),
            evidence,
        )

    def _validate_au(
        self, components: Sequence[BlendComponent], claims: LabelClaims
    ) -> LabelClaimDecision:
        issues: list[str] = []
        evidence = ("source:au_regulations",)
        countries = {_norm(c.country) for c in components}
        if len(countries) > 1 and not claims.country_proportions_shown:
            issues.append("Australian labels for multi-country wine must disclose country proportions.")

        if claims.variety_names:
            shares = _shares_for_names(components, claims.variety_names, _sum_grape)
            if len(shares) == 1:
                if shares[0][1] + 1e-9 < 85:
                    issues.append("A single Australian variety claim requires at least 85%.")
            else:
                named_total = sum(share for _, share in shares)
                if named_total + 1e-9 < 85:
                    issues.append("Named Australian varieties must together comprise at least 85%.")
                unnamed = [
                    _sum_grape(components, grape)
                    for grape in {c.grape for c in components}
                    if _norm(grape) not in {_norm(name) for name in claims.variety_names}
                ]
                if unnamed and any(share <= max(unnamed) + 1e-9 for _, share in shares):
                    issues.append("Each named variety must exceed every unnamed variety.")
                if not _descending(shares):
                    issues.append("Named Australian varieties must be listed in descending proportion.")

        if claims.origin_names:
            shares = _shares_for_names(components, claims.origin_names, _sum_origin)
            if len(shares) == 1:
                if shares[0][1] + 1e-9 < 85:
                    issues.append("A single Australian GI/place claim requires at least 85%.")
            else:
                if len(shares) > 3:
                    issues.append("No more than three Australian GIs/place names may be claimed.")
                if sum(share for _, share in shares) + 1e-9 < 95:
                    issues.append("Two or three Australian origin claims must together comprise at least 95%.")
                if any(share + 1e-9 < 5 for _, share in shares):
                    issues.append("Each named Australian origin must comprise at least 5%.")
                if not _descending(shares):
                    issues.append("Named Australian origins must be listed in descending proportion.")

        if claims.vintage_years:
            shares = [(str(year), _sum_vintage(components, year)) for year in claims.vintage_years]
            if len(shares) == 1:
                if shares[0][1] + 1e-9 < 85:
                    issues.append("A single Australian vintage claim requires at least 85%.")
            else:
                actual = {c.vintage for c in components if c.vintage is not None}
                if set(claims.vintage_years) != actual:
                    issues.append("A multi-vintage Australian claim must list every vintage used.")
                if not _descending(shares):
                    issues.append("Australian vintages must be listed in descending proportion.")

        return LabelClaimDecision(
            not issues,
            "au_label_claim_eligible" if not issues else "au_label_claim_violation",
            tuple(issues),
            evidence,
        )

    def _validate_nz(
        self, components: Sequence[BlendComponent], claims: LabelClaims
    ) -> LabelClaimDecision:
        issues: list[str] = []
        evidence = ("source:nz_mpi_labelling", "source:nz_iponz_gi")
        named_varieties = {_norm(name) for name in claims.variety_names}
        named_origins = {_norm(name) for name in claims.origin_names}
        named_vintages = set(claims.vintage_years)

        def check_dimension(
            label: str,
            shares: list[tuple[object, float]],
            actual: list[tuple[object, float]],
            key,
        ) -> None:
            if not shares:
                return
            plural = "varieties" if label == "variety" else label + "s"
            if sum(share for _, share in shares) + 1e-9 < 85:
                issues.append(f"Named New Zealand {plural} must together comprise at least 85%.")
            if not _descending(shares):
                issues.append(f"Named New Zealand {plural} must be listed in descending proportion.")
            if len(shares) > 1:
                min_named = min(share for _, share in shares)
                named_keys = {key(name) for name, _share in shares}
                if any(
                    share > min_named + 1e-9
                    for name, share in actual
                    if key(name) not in named_keys
                ):
                    issues.append(
                        f"A higher-proportion unnamed {label} cannot be omitted in favor of a lower named one."
                    )

        if claims.variety_names:
            shares = [(name, _sum_grape(components, name)) for name in claims.variety_names]
            actual_names = {c.grape for c in components}
            actual = [(name, _sum_grape(components, name)) for name in actual_names]
            check_dimension("variety", shares, actual, lambda value: _norm(str(value)))

        if claims.origin_names:
            shares = [(name, _sum_origin(components, name)) for name in claims.origin_names]
            actual_names = {c.origins[0] for c in components if c.origins}
            actual = [(name, _sum_origin(components, name)) for name in actual_names]
            check_dimension("area", shares, actual, lambda value: _norm(str(value)))

        if claims.vintage_years:
            shares = [(year, _sum_vintage(components, year)) for year in claims.vintage_years]
            actual_years = {c.vintage for c in components if c.vintage is not None}
            actual = [(year, _sum_vintage(components, year)) for year in actual_years]
            check_dimension("vintage", shares, actual, lambda value: int(value))

        dimensions = sum(bool(x) for x in (claims.variety_names, claims.origin_names, claims.vintage_years))
        if dimensions >= 2:
            intersection = sum(
                c.volume_pct
                for c in components
                if (not named_varieties or _norm(c.grape) in named_varieties)
                and (not named_origins or any(_norm(origin) in named_origins for origin in c.origins))
                and (not named_vintages or c.vintage in named_vintages)
            )
            if intersection + 1e-9 < 85:
                issues.append("At least 85% must satisfy the claimed variety/vintage/area combination.")

        if claims.registered_nz_gi:
            if len(claims.origin_names) != 1:
                issues.append("Registered New Zealand GI validation requires one registered GI claim.")
            elif _sum_origin(components, claims.origin_names[0]) + 1e-9 < 85:
                issues.append("A registered New Zealand GI requires at least 85% from that GI.")
            if any(_norm(c.country) != _norm("New Zealand") for c in components):
                issues.append("All wine outside the claimed registered GI must still be from New Zealand.")

        return LabelClaimDecision(
            not issues,
            "nz_label_claim_eligible" if not issues else "nz_label_claim_violation",
            tuple(issues),
            evidence,
        )

    def stats(self) -> dict[str, int]:
        return {
            "jurisdiction_label_rule_sets": 3,
            "us_label_rule_dimensions": 3,
            "au_label_rule_dimensions": 4,
            "nz_label_rule_dimensions": 4,
        }
