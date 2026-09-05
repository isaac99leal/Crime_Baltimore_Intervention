"""Hard origin/grape constraints for the wine knowledge v2 simulation.

The rulebook distinguishes three facts that must not be conflated:

* legal appellation eligibility;
* evidence that a cultivar is commercially planted in a country;
* experimental planting/winemaking.

A simulator may explore experimental plantings, but it must never silently convert
an unverified or illegal grape/appellation combination into an appellation wine.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .catalog import normalize_name
from .expanded_catalog import WorldWineKnowledgeCatalog

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]
DEFAULT_REGIONS_PATH = REPO_ROOT / "somm_simulator" / "data" / "regions.json"


class OriginConstraintError(ValueError):
    """Raised when a requested wine origin or planting violates a hard rule."""


@dataclass(frozen=True)
class RegionRule:
    id: str
    country: str
    major_region: str
    sub_region: str | None = None
    commune: str | None = None
    primary_grapes: tuple[str, ...] = ()
    allowed_grapes: tuple[str, ...] = ()
    max_yield_hl_ha: float | None = None
    min_alcohol_pct: float | None = None
    required_aging_months: int | None = None
    classification_system: str = ""

    @property
    def specificity(self) -> int:
        return 3 if self.commune else 2 if self.sub_region else 1

    @property
    def legal_grape_rule_known(self) -> bool:
        return bool(self.allowed_grapes)


@dataclass(frozen=True)
class OriginDecision:
    eligible: bool
    status: str
    label_scope: str
    canonical_grapes: tuple[str, ...]
    rule_id: str | None = None
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def require(self) -> "OriginDecision":
        if not self.eligible:
            raise OriginConstraintError("; ".join(self.issues) or self.status)
        return self


def _positive(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


class RegionGrapeRulebook:
    """Resolve geographic rules and prevent impossible appellation/grape claims."""

    def __init__(
        self,
        regions_path: Path | None = None,
        *,
        catalog: WorldWineKnowledgeCatalog | None = None,
    ) -> None:
        self.regions_path = regions_path or DEFAULT_REGIONS_PATH
        self.catalog = catalog or WorldWineKnowledgeCatalog()
        self.rules: list[RegionRule] = []
        self._name_index: dict[tuple[str, str], list[RegionRule]] = {}
        self._load()

    @staticmethod
    def _norm(value: str | None) -> str:
        return normalize_name(value or "")

    def _index(self, rule: RegionRule, *names: str | None) -> None:
        country = self._norm(rule.country)
        for name in names:
            key = self._norm(name)
            if key:
                self._name_index.setdefault((country, key), []).append(rule)

    def _load(self) -> None:
        doc = json.loads(self.regions_path.read_text(encoding="utf-8"))
        rules: list[RegionRule] = []
        for country_row in doc.get("regions", []):
            country = str(country_row.get("country", "")).strip()
            if not country:
                continue
            for region in country_row.get("wine_regions", []):
                major = str(region.get("name", "")).strip()
                region_primary = tuple(str(g) for g in region.get("primary_grapes", []) if str(g).strip())
                region_rule = RegionRule(
                    id=f"region:{self._norm(country)}:{self._norm(major)}",
                    country=country,
                    major_region=major,
                    primary_grapes=region_primary,
                    classification_system=str(region.get("classification_system", "")),
                )
                rules.append(region_rule)
                self._index(region_rule, major)
                for sub in region.get("sub_regions", []):
                    sub_name = str(sub.get("name", "")).strip()
                    sub_primary = tuple(
                        str(g) for g in sub.get("primary_grapes", region_primary) if str(g).strip()
                    )
                    sub_rule = RegionRule(
                        id=f"{region_rule.id}:{self._norm(sub_name)}",
                        country=country,
                        major_region=major,
                        sub_region=sub_name,
                        primary_grapes=sub_primary,
                        classification_system=str(region.get("classification_system", "")),
                    )
                    rules.append(sub_rule)
                    self._index(sub_rule, sub_name)
                    for commune in sub.get("communes", []):
                        commune_name = str(commune.get("name", "")).strip()
                        primary = tuple(
                            str(g)
                            for g in commune.get("primary_grapes", sub_primary)
                            if str(g).strip()
                        )
                        allowed = tuple(
                            str(g) for g in commune.get("allowed_grapes", []) if str(g).strip()
                        )
                        max_yield = _positive(commune.get("max_yield_hl_ha"))
                        min_alcohol = _positive(commune.get("min_alcohol"))
                        required_aging = commune.get("required_aging_months")
                        try:
                            required_aging_i = int(required_aging) if required_aging else None
                        except (TypeError, ValueError):
                            required_aging_i = None
                        rule = RegionRule(
                            id=f"{sub_rule.id}:{self._norm(commune_name)}",
                            country=country,
                            major_region=major,
                            sub_region=sub_name,
                            commune=commune_name,
                            primary_grapes=primary,
                            allowed_grapes=allowed,
                            max_yield_hl_ha=max_yield,
                            min_alcohol_pct=min_alcohol,
                            required_aging_months=required_aging_i,
                            classification_system=str(
                                commune.get("classification_system")
                                or region.get("classification_system", "")
                            ),
                        )
                        rules.append(rule)
                        self._index(rule, commune_name)
        self.rules = rules

    def resolve(
        self,
        *,
        country: str,
        appellation: str | None = None,
        region: str | None = None,
        sub_region: str | None = None,
        commune: str | None = None,
    ) -> RegionRule | None:
        country_key = self._norm(country)
        requested = [commune, appellation, sub_region, region]
        candidates: list[RegionRule] = []
        for name in requested:
            key = self._norm(name)
            if key:
                candidates.extend(self._name_index.get((country_key, key), []))
        if not candidates:
            return None

        region_key = self._norm(region)
        sub_key = self._norm(sub_region)
        commune_key = self._norm(commune or appellation)

        def score(rule: RegionRule) -> tuple[int, int, int, int]:
            exact_commune = int(bool(commune_key) and self._norm(rule.commune) == commune_key)
            exact_sub = int(bool(sub_key) and self._norm(rule.sub_region) == sub_key)
            exact_region = int(bool(region_key) and self._norm(rule.major_region) == region_key)
            return (exact_commune, exact_sub, exact_region, rule.specificity)

        return max(candidates, key=score)

    def canonical_grape(self, name: str) -> str:
        grape = self.catalog.grape(name)
        return grape.name if grape is not None else name.strip()

    def same_grape(self, left: str, right: str) -> bool:
        l = self.catalog.grape(left)
        r = self.catalog.grape(right)
        if l is not None and r is not None:
            return l.id == r.id
        if l is not None:
            return any(self._norm(right) == self._norm(n) for n in (l.name, *l.aliases))
        if r is not None:
            return any(self._norm(left) == self._norm(n) for n in (r.name, *r.aliases))
        return self._norm(left) == self._norm(right)

    def _blend(
        self, grapes: Mapping[str, float] | Sequence[str] | str
    ) -> tuple[list[tuple[str, float | None]], list[str]]:
        issues: list[str] = []
        if isinstance(grapes, str):
            rows = [(grapes, None)]
        elif isinstance(grapes, Mapping):
            rows = []
            total = 0.0
            for name, pct in grapes.items():
                try:
                    pct_f = float(pct)
                except (TypeError, ValueError):
                    issues.append(f"Invalid blend percentage for {name!r}")
                    continue
                if pct_f <= 0 or pct_f > 100:
                    issues.append(f"Blend percentage for {name!r} must be >0 and <=100")
                total += pct_f
                rows.append((str(name), pct_f))
            if rows and abs(total - 100.0) > 0.25:
                issues.append(f"Blend percentages must sum to 100 (got {total:.2f})")
        else:
            rows = [(str(name), None) for name in grapes]
        if not rows:
            issues.append("At least one grape is required")
        return rows, issues

    @staticmethod
    def _area_at_year(row: object, year: int) -> float | None:
        attrs = (
            ("area_2023_ha", 2023),
            ("area_2016_ha", 2016),
            ("area_2010_ha", 2010),
            ("area_2000_ha", 2000),
        )
        eligible = [(attr, y) for attr, y in attrs if y <= year]
        if not eligible:
            eligible = [("area_2000_ha", 2000)]
        for attr, _ in eligible:
            value = getattr(row, attr, None)
            if value is not None and value > 0:
                return float(value)
        return None

    def commercial_evidence(
        self, grape_name: str, country: str, *, vintage_year: int = 2023
    ) -> tuple[bool, tuple[str, ...]]:
        evidence: list[str] = []
        for row in self.catalog.area_for(grape_name, country=country):
            area = self._area_at_year(row, vintage_year)
            if area is not None:
                evidence.append(f"acreage_census:{country}:{area:.6g}ha")
        grape = self.catalog.grape(grape_name)
        aliases = {self._norm(grape_name)}
        if grape is not None:
            aliases.add(self._norm(grape.name))
            aliases.update(self._norm(a) for a in grape.aliases)
        for obs in self.catalog.commercial_observations:
            if (
                self._norm(obs.country) == self._norm(country)
                and self._norm(obs.variety) in aliases
            ):
                evidence.append(f"market_observation:{obs.organization}")
        return bool(evidence), tuple(sorted(set(evidence)))

    def evaluate(
        self,
        *,
        country: str,
        grapes: Mapping[str, float] | Sequence[str] | str,
        label_scope: str,
        vintage_year: int = 2023,
        appellation: str | None = None,
        region: str | None = None,
        sub_region: str | None = None,
        commune: str | None = None,
        experimental: bool = False,
    ) -> OriginDecision:
        scope = label_scope.strip().casefold()
        if scope not in {"regulated_gi", "country_wine", "experimental"}:
            return OriginDecision(
                eligible=False,
                status="invalid_label_scope",
                label_scope=scope,
                canonical_grapes=(),
                issues=(f"Unsupported label_scope {label_scope!r}",),
            )

        blend, issues = self._blend(grapes)
        canonical = tuple(self.canonical_grape(name) for name, _ in blend)
        if issues:
            return OriginDecision(
                eligible=False,
                status="invalid_blend",
                label_scope=scope,
                canonical_grapes=canonical,
                issues=tuple(issues),
            )

        if scope == "regulated_gi":
            rule = self.resolve(
                country=country,
                appellation=appellation,
                region=region,
                sub_region=sub_region,
                commune=commune,
            )
            if rule is None:
                return OriginDecision(
                    eligible=False,
                    status="unresolved_appellation",
                    label_scope=scope,
                    canonical_grapes=canonical,
                    issues=(
                        "The requested regulated origin does not resolve to a rule; automatic GI generation is blocked.",
                    ),
                )
            if not rule.legal_grape_rule_known:
                return OriginDecision(
                    eligible=False,
                    status="legal_grape_rule_unverified",
                    label_scope=scope,
                    canonical_grapes=canonical,
                    rule_id=rule.id,
                    issues=(
                        "This origin lacks an explicit allowed-grape rule in the current registry. The simulator must not assume primary grapes are the legal list.",
                    ),
                )
            forbidden = [
                grape
                for grape in canonical
                if not any(self.same_grape(grape, allowed) for allowed in rule.allowed_grapes)
            ]
            if forbidden:
                return OriginDecision(
                    eligible=False,
                    status="grape_not_permitted_for_appellation",
                    label_scope=scope,
                    canonical_grapes=canonical,
                    rule_id=rule.id,
                    issues=tuple(
                        f"{grape} is not in the explicit allowed-grape list for {rule.commune or rule.sub_region or rule.major_region}"
                        for grape in forbidden
                    ),
                )
            return OriginDecision(
                eligible=True,
                status="appellation_eligible",
                label_scope=scope,
                canonical_grapes=canonical,
                rule_id=rule.id,
                warnings=(
                    "Experimental production flag is set; legal process rules beyond grape eligibility still require validation.",
                ) if experimental else (),
                evidence=tuple(f"allowed_grape:{g}" for g in rule.allowed_grapes),
            )

        evidence: list[str] = []
        missing: list[str] = []
        for grape in canonical:
            ok, grape_evidence = self.commercial_evidence(
                grape, country, vintage_year=vintage_year
            )
            if ok:
                evidence.extend(grape_evidence)
            else:
                missing.append(grape)

        if missing and not (experimental or scope == "experimental"):
            return OriginDecision(
                eligible=False,
                status="no_country_cultivation_evidence",
                label_scope=scope,
                canonical_grapes=canonical,
                issues=tuple(
                    f"No census or market evidence currently supports {grape} as a commercial cultivar in {country}; use an experimental wine context instead."
                    for grape in missing
                ),
                evidence=tuple(sorted(set(evidence))),
            )

        warnings = tuple(
            f"{grape} has no commercial-country evidence and is allowed only as experimental."
            for grape in missing
        )
        return OriginDecision(
            eligible=True,
            status="experimental_origin" if missing else "country_origin_supported",
            label_scope=scope,
            canonical_grapes=canonical,
            warnings=warnings,
            evidence=tuple(sorted(set(evidence))),
        )

    def stats(self) -> dict[str, int]:
        strict = [rule for rule in self.rules if rule.legal_grape_rule_known]
        return {
            "region_rules": len(self.rules),
            "strict_allowed_grape_rules": len(strict),
            "rules_with_yield_limits": sum(1 for r in self.rules if r.max_yield_hl_ha),
            "rules_with_min_alcohol": sum(1 for r in self.rules if r.min_alcohol_pct),
            "rules_with_required_aging": sum(1 for r in self.rules if r.required_aging_months),
        }
