"""Authoritative production-specification rules for protected wine origins.

The legacy region database is useful geographic context but its ``primary_grapes``
field is not a legal authorization list. This module loads separately sourced legal
specifications and evaluates grape blends, vineyard/production limits, analytical
limits, and release/process requirements. Unknown rules fail closed when complete
validation is requested.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .catalog import normalize_name

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_PATH = DATA_DIR / "legal_gi_specs_seed.json"
SUPPLEMENT_PATH = DATA_DIR / "legal_gi_specs_supplement.json"
BURGUNDY_PATH = DATA_DIR / "legal_gi_specs_burgundy.json"
COTE_DE_NUITS_PATH = DATA_DIR / "legal_gi_specs_cote_de_nuits.json"


def _default_data_paths() -> list[Path]:
    """Load every reviewed legal-spec tranche in deterministic filename order."""
    return sorted(DATA_DIR.glob("legal_gi_specs_*.json"), key=lambda path: path.name)


@dataclass(frozen=True)
class GrapeConstraint:
    grape: str
    min_pct: float = 0.0
    max_pct: float = 100.0


@dataclass(frozen=True)
class LegalWineSpec:
    id: str
    country: str
    appellation: str
    variant: str = "standard"
    aliases: tuple[str, ...] = ()
    wine_style: str | None = None
    allowed_grapes: tuple[str, ...] = ()
    grape_constraints: tuple[GrapeConstraint, ...] = ()
    vineyard_adaptation_grapes: tuple[str, ...] = ()
    vineyard_adaptation_max_pct: float | None = None
    max_yield_t_ha: float | None = None
    max_yield_hl_ha: float | None = None
    grape_to_wine_yield_pct: float | None = None
    min_must_sugar_g_l: float | None = None
    min_potential_alcohol_pct: float | None = None
    min_final_alcohol_pct: float | None = None
    max_total_alcohol_pct: float | None = None
    min_total_acidity_g_l: float | None = None
    min_dry_extract_g_l: float | None = None
    max_residual_sugar_g_l: float | None = None
    max_malic_acid_g_l: float | None = None
    min_total_aging_months: int | None = None
    min_wood_aging_months: int | None = None
    min_bottle_aging_months: int | None = None
    min_elevage_year_offset: int | None = None
    min_elevage_until_month: int | None = None
    min_elevage_until_day: int | None = None
    release_year_offset: int | None = None
    earliest_release_month: int | None = None
    earliest_release_day: int | None = None
    required_method: str | None = None
    manual_harvest_required: bool = False
    bottling_in_origin_required: bool = False
    effective_from: str | None = None
    effective_to: str | None = None
    regulatory_status: str = "current"
    source_ids: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class LegalSpecDecision:
    eligible: bool
    spec_id: str | None
    status: str
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def require(self) -> "LegalSpecDecision":
        if not self.eligible:
            raise ValueError("; ".join(self.issues) or self.status)
        return self


@dataclass(frozen=True)
class ProductionDecision:
    eligible: bool
    spec_id: str
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReleaseDecision:
    eligible: bool
    spec_id: str
    issues: tuple[str, ...] = ()


def _f(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _i(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _valid_month_day(month: int | None, day: int | None) -> bool:
    if month is None or day is None:
        return False
    if month < 1 or month > 12 or day < 1 or day > 31:
        return False
    if month in {4, 6, 9, 11} and day > 30:
        return False
    if month == 2 and day > 29:
        return False
    return True


class LegalSpecRegistry:
    """Load and evaluate reviewed protected-origin production specifications."""

    def __init__(self, data_path: Path | None = None) -> None:
        paths = [Path(data_path)] if data_path is not None else _default_data_paths()
        documents: list[dict[str, object]] = []
        for path in paths:
            if not path.exists():
                if data_path is not None:
                    raise FileNotFoundError(path)
                continue
            doc = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise ValueError(f"{path.name} must contain a JSON object")
            documents.append(doc)

        self.sources: dict[str, dict[str, object]] = {}
        raw_specs: list[dict[str, object]] = []
        seen_spec_ids: set[str] = set()
        for doc in documents:
            for source_id, source in dict(doc.get("sources", {})).items():
                source_row = dict(source)
                existing = self.sources.get(str(source_id))
                if existing is not None and existing != source_row:
                    raise ValueError(f"Conflicting legal source definition: {source_id}")
                self.sources[str(source_id)] = source_row
            for row in doc.get("specs", []):
                if not isinstance(row, dict):
                    continue
                spec_id = str(row.get("id") or "")
                if not spec_id:
                    raise ValueError("Legal specification is missing an id")
                if spec_id in seen_spec_ids:
                    raise ValueError(f"Duplicate legal specification id: {spec_id}")
                seen_spec_ids.add(spec_id)
                raw_specs.append(row)

        self.specs: list[LegalWineSpec] = []
        self._index: dict[tuple[str, str], list[LegalWineSpec]] = {}
        for row in raw_specs:
            constraints = tuple(
                GrapeConstraint(
                    grape=str(item["grape"]),
                    min_pct=float(item.get("min_pct", 0.0)),
                    max_pct=float(item.get("max_pct", 100.0)),
                )
                for item in row.get("grape_constraints", [])
            )
            source_ids = tuple(row.get("source_ids", []))
            unknown_sources = [sid for sid in source_ids if sid not in self.sources]
            if unknown_sources:
                raise ValueError(
                    f"{row['id']} references unknown legal sources: {unknown_sources}"
                )
            spec = LegalWineSpec(
                id=str(row["id"]),
                country=str(row["country"]),
                appellation=str(row["appellation"]),
                variant=str(row.get("variant", "standard")),
                aliases=tuple(row.get("aliases", [])),
                wine_style=row.get("wine_style"),
                allowed_grapes=tuple(row.get("allowed_grapes", [])),
                grape_constraints=constraints,
                vineyard_adaptation_grapes=tuple(row.get("vineyard_adaptation_grapes", [])),
                vineyard_adaptation_max_pct=_f(row.get("vineyard_adaptation_max_pct")),
                max_yield_t_ha=_f(row.get("max_yield_t_ha")),
                max_yield_hl_ha=_f(row.get("max_yield_hl_ha")),
                grape_to_wine_yield_pct=_f(row.get("grape_to_wine_yield_pct")),
                min_must_sugar_g_l=_f(row.get("min_must_sugar_g_l")),
                min_potential_alcohol_pct=_f(row.get("min_potential_alcohol_pct")),
                min_final_alcohol_pct=_f(row.get("min_final_alcohol_pct")),
                max_total_alcohol_pct=_f(row.get("max_total_alcohol_pct")),
                min_total_acidity_g_l=_f(row.get("min_total_acidity_g_l")),
                min_dry_extract_g_l=_f(row.get("min_dry_extract_g_l")),
                max_residual_sugar_g_l=_f(row.get("max_residual_sugar_g_l")),
                max_malic_acid_g_l=_f(row.get("max_malic_acid_g_l")),
                min_total_aging_months=_i(row.get("min_total_aging_months")),
                min_wood_aging_months=_i(row.get("min_wood_aging_months")),
                min_bottle_aging_months=_i(row.get("min_bottle_aging_months")),
                min_elevage_year_offset=_i(row.get("min_elevage_year_offset")),
                min_elevage_until_month=_i(row.get("min_elevage_until_month")),
                min_elevage_until_day=_i(row.get("min_elevage_until_day")),
                release_year_offset=_i(row.get("release_year_offset")),
                earliest_release_month=_i(row.get("earliest_release_month")),
                earliest_release_day=_i(row.get("earliest_release_day")),
                required_method=row.get("required_method"),
                manual_harvest_required=bool(row.get("manual_harvest_required", False)),
                bottling_in_origin_required=bool(row.get("bottling_in_origin_required", False)),
                effective_from=row.get("effective_from"),
                effective_to=row.get("effective_to"),
                regulatory_status=str(row.get("regulatory_status", "current")),
                source_ids=source_ids,
                notes=str(row.get("notes", "")),
            )
            if (spec.min_elevage_until_month is None) != (spec.min_elevage_until_day is None):
                raise ValueError(f"{spec.id} must define both elevage month and day")
            if spec.min_elevage_until_month is not None and not _valid_month_day(
                spec.min_elevage_until_month, spec.min_elevage_until_day
            ):
                raise ValueError(f"{spec.id} has an invalid elevage month/day")
            if (spec.earliest_release_month is None) != (spec.earliest_release_day is None):
                raise ValueError(f"{spec.id} must define both release month and day")
            if spec.earliest_release_month is not None and not _valid_month_day(
                spec.earliest_release_month, spec.earliest_release_day
            ):
                raise ValueError(f"{spec.id} has an invalid release month/day")
            self.specs.append(spec)
            country = normalize_name(spec.country)
            for name in (spec.appellation, *spec.aliases):
                self._index.setdefault((country, normalize_name(name)), []).append(spec)

    def resolve(
        self,
        *,
        country: str,
        appellation: str | None = None,
        region: str | None = None,
        sub_region: str | None = None,
        commune: str | None = None,
        variant: str | None = None,
    ) -> LegalWineSpec | None:
        country_key = normalize_name(country)
        candidates: list[LegalWineSpec] = []
        for name in (commune, appellation, sub_region, region):
            if name:
                candidates.extend(self._index.get((country_key, normalize_name(name)), []))
        if not candidates:
            return None
        variant_key = normalize_name(variant or "standard")
        exact = [s for s in candidates if normalize_name(s.variant) == variant_key]
        if exact:
            return exact[0]
        standard = [s for s in candidates if normalize_name(s.variant) == "standard"]
        return standard[0] if standard else None

    @staticmethod
    def _blend_rows(
        grapes: Mapping[str, float] | Sequence[str] | str,
    ) -> tuple[list[tuple[str, float | None]], list[str]]:
        issues: list[str] = []
        if isinstance(grapes, str):
            rows = [(grapes, 100.0)]
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
            seq = [str(x) for x in grapes]
            rows = [(seq[0], 100.0)] if len(seq) == 1 else [(x, None) for x in seq]
        if not rows:
            issues.append("At least one grape is required")
        return rows, issues

    def evaluate_blend(
        self,
        spec: LegalWineSpec,
        grapes: Mapping[str, float] | Sequence[str] | str,
        *,
        canonicalize: Callable[[str], str] = lambda value: value,
        same_grape: Callable[[str, str], bool] | None = None,
    ) -> LegalSpecDecision:
        same = same_grape or (lambda a, b: normalize_name(a) == normalize_name(b))
        rows, issues = self._blend_rows(grapes)
        canonical = [(canonicalize(name), pct) for name, pct in rows]
        if issues:
            return LegalSpecDecision(False, spec.id, "invalid_blend", tuple(issues))
        if not spec.allowed_grapes:
            return LegalSpecDecision(
                False,
                spec.id,
                "legal_grape_rule_unverified",
                ("The sourced specification has no explicit allowed-grape list.",),
            )

        forbidden = [
            name
            for name, _ in canonical
            if not any(same(name, allowed) for allowed in spec.allowed_grapes)
        ]
        if forbidden:
            return LegalSpecDecision(
                False,
                spec.id,
                "grape_not_permitted_for_appellation",
                tuple(
                    f"{name} is not authorized by {spec.appellation} specification {spec.id}"
                    for name in forbidden
                ),
                evidence=tuple(f"source:{sid}" for sid in spec.source_ids),
            )

        if spec.grape_constraints:
            if any(pct is None for _, pct in canonical):
                return LegalSpecDecision(
                    False,
                    spec.id,
                    "blend_percentages_required",
                    ("This appellation has grape-percentage rules; explicit blend percentages are required.",),
                )
            for constraint in spec.grape_constraints:
                pct = sum(
                    float(value or 0.0)
                    for name, value in canonical
                    if same(name, constraint.grape)
                )
                if pct + 1e-9 < constraint.min_pct or pct - 1e-9 > constraint.max_pct:
                    issues.append(
                        f"{constraint.grape} must be {constraint.min_pct:g}–{constraint.max_pct:g}% for {spec.appellation}; got {pct:g}%"
                    )
        if issues:
            return LegalSpecDecision(
                False,
                spec.id,
                "blend_percentage_violation",
                tuple(issues),
                evidence=tuple(f"source:{sid}" for sid in spec.source_ids),
            )
        return LegalSpecDecision(
            True,
            spec.id,
            "legal_spec_eligible",
            evidence=tuple(f"source:{sid}" for sid in spec.source_ids),
        )

    def validate_production(
        self,
        spec: LegalWineSpec,
        *,
        vineyard_yield_t_ha: float | None = None,
        wine_yield_hl_ha: float | None = None,
        actual_grape_to_wine_yield_pct: float | None = None,
        must_sugar_g_l: float | None = None,
        potential_alcohol_pct: float | None = None,
        bottled_in_origin: bool | None = None,
        require_complete: bool = False,
    ) -> ProductionDecision:
        """Validate machine-modeled vineyard, maturity and pre-release limits."""
        issues: list[str] = []

        if spec.max_yield_t_ha is not None:
            if vineyard_yield_t_ha is None:
                if require_complete:
                    issues.append("Vineyard yield is required for complete legal validation")
            elif vineyard_yield_t_ha > spec.max_yield_t_ha + 1e-9:
                issues.append(f"Vineyard yield must not exceed {spec.max_yield_t_ha:g} t/ha")

        if spec.max_yield_hl_ha is not None:
            if wine_yield_hl_ha is None:
                if require_complete:
                    issues.append("Wine yield is required for complete legal validation")
            elif wine_yield_hl_ha > spec.max_yield_hl_ha + 1e-9:
                issues.append(f"Wine yield must not exceed {spec.max_yield_hl_ha:g} hL/ha")

        if spec.grape_to_wine_yield_pct is not None:
            if actual_grape_to_wine_yield_pct is None:
                if require_complete:
                    issues.append("Grape-to-wine yield is required for complete legal validation")
            elif actual_grape_to_wine_yield_pct > spec.grape_to_wine_yield_pct + 1e-9:
                issues.append(
                    f"Grape-to-wine yield must not exceed {spec.grape_to_wine_yield_pct:g}%"
                )

        if spec.min_must_sugar_g_l is not None:
            if must_sugar_g_l is None:
                if require_complete:
                    issues.append("Must sugar is required for complete maturity validation")
            elif must_sugar_g_l + 1e-9 < spec.min_must_sugar_g_l:
                issues.append(f"Must sugar must be at least {spec.min_must_sugar_g_l:g} g/L")

        if spec.min_potential_alcohol_pct is not None:
            if potential_alcohol_pct is None:
                if require_complete:
                    issues.append("Potential alcohol is required for complete legal validation")
            elif potential_alcohol_pct + 1e-9 < spec.min_potential_alcohol_pct:
                issues.append(
                    f"Potential alcohol must be at least {spec.min_potential_alcohol_pct:g}%"
                )

        if spec.bottling_in_origin_required and bottled_in_origin is not True:
            issues.append("Bottling in the protected origin is required")

        return ProductionDecision(not issues, spec.id, tuple(issues))

    def validate_release(
        self,
        spec: LegalWineSpec,
        *,
        total_aging_months: int,
        wood_aging_months: int = 0,
        bottle_aging_months: int = 0,
        method: str | None = None,
        manual_harvest: bool | None = None,
        final_alcohol_pct: float | None = None,
        total_alcohol_pct: float | None = None,
        total_acidity_g_l: float | None = None,
        dry_extract_g_l: float | None = None,
        residual_sugar_g_l: float | None = None,
        malic_acid_g_l: float | None = None,
        vintage_year: int | None = None,
        elevage_end_year: int | None = None,
        elevage_end_month: int | None = None,
        elevage_end_day: int | None = None,
        release_year: int | None = None,
        release_month: int | None = None,
        release_day: int | None = None,
        require_complete: bool = False,
    ) -> ReleaseDecision:
        issues: list[str] = []
        if spec.min_total_aging_months is not None and total_aging_months < spec.min_total_aging_months:
            issues.append(f"Total aging must be at least {spec.min_total_aging_months} months")
        if spec.min_wood_aging_months is not None and wood_aging_months < spec.min_wood_aging_months:
            issues.append(f"Wood aging must be at least {spec.min_wood_aging_months} months")
        if spec.min_bottle_aging_months is not None and bottle_aging_months < spec.min_bottle_aging_months:
            issues.append(f"Bottle aging must be at least {spec.min_bottle_aging_months} months")
        if spec.required_method and normalize_name(method or "") != normalize_name(spec.required_method):
            issues.append(f"Required production method: {spec.required_method}")
        if spec.manual_harvest_required and manual_harvest is not True:
            issues.append("Manual harvest is required")
        if spec.min_final_alcohol_pct is not None and (
            final_alcohol_pct is None or final_alcohol_pct < spec.min_final_alcohol_pct
        ):
            issues.append(f"Final alcohol must be at least {spec.min_final_alcohol_pct:g}% vol")
        if spec.max_total_alcohol_pct is not None:
            if total_alcohol_pct is None:
                if require_complete:
                    issues.append("Total alcoholic strength is required for complete legal validation")
            elif total_alcohol_pct > spec.max_total_alcohol_pct + 1e-9:
                issues.append(
                    f"Total alcoholic strength must not exceed {spec.max_total_alcohol_pct:g}% vol"
                )
        if spec.min_total_acidity_g_l is not None and (
            total_acidity_g_l is None or total_acidity_g_l < spec.min_total_acidity_g_l
        ):
            issues.append(f"Total acidity must be at least {spec.min_total_acidity_g_l:g} g/L")
        if spec.min_dry_extract_g_l is not None and (
            dry_extract_g_l is None or dry_extract_g_l < spec.min_dry_extract_g_l
        ):
            issues.append(f"Dry extract must be at least {spec.min_dry_extract_g_l:g} g/L")

        if spec.max_residual_sugar_g_l is not None:
            if residual_sugar_g_l is None:
                if require_complete:
                    issues.append("Residual sugar is required for complete legal validation")
            elif residual_sugar_g_l > spec.max_residual_sugar_g_l + 1e-9:
                issues.append(
                    f"Residual sugar must not exceed {spec.max_residual_sugar_g_l:g} g/L"
                )

        if spec.max_malic_acid_g_l is not None:
            if malic_acid_g_l is None:
                if require_complete:
                    issues.append("Malic acid is required for complete legal validation")
            elif malic_acid_g_l > spec.max_malic_acid_g_l + 1e-9:
                issues.append(f"Malic acid must not exceed {spec.max_malic_acid_g_l:g} g/L")

        if spec.min_elevage_until_month is not None and spec.min_elevage_until_day is not None:
            if vintage_year is None or elevage_end_year is None or elevage_end_month is None or elevage_end_day is None:
                if require_complete:
                    issues.append("Exact elevage end date is required for complete legal validation")
            else:
                required_elevage_year = vintage_year + (spec.min_elevage_year_offset or 0)
                actual = (elevage_end_year, elevage_end_month, elevage_end_day)
                required = (
                    required_elevage_year,
                    spec.min_elevage_until_month,
                    spec.min_elevage_until_day,
                )
                if actual < required:
                    issues.append(
                        f"Elevage must continue through {required_elevage_year:04d}-{spec.min_elevage_until_month:02d}-{spec.min_elevage_until_day:02d}"
                    )

        if spec.release_year_offset is not None:
            if vintage_year is None or release_year is None:
                if require_complete:
                    issues.append(
                        "Vintage year and release year are required for complete release-date validation"
                    )
            else:
                required_year = vintage_year + spec.release_year_offset
                if spec.earliest_release_month is not None and spec.earliest_release_day is not None:
                    if release_month is None or release_day is None:
                        if require_complete:
                            issues.append("Exact release month/day is required for complete release-date validation")
                    elif (release_year, release_month, release_day) < (
                        required_year,
                        spec.earliest_release_month,
                        spec.earliest_release_day,
                    ):
                        issues.append(
                            f"Consumer release must not occur before {required_year:04d}-{spec.earliest_release_month:02d}-{spec.earliest_release_day:02d}"
                        )
                elif release_year < required_year:
                    issues.append(
                        f"Release year must be at least {required_year} for vintage {vintage_year}"
                    )

        return ReleaseDecision(not issues, spec.id, tuple(issues))

    def stats(self) -> dict[str, int]:
        appellations = {
            (normalize_name(s.country), normalize_name(s.appellation)) for s in self.specs
        }
        return {
            "sourced_legal_wine_specs": len(self.specs),
            "sourced_appellations_with_strict_specs": len(appellations),
            "legal_specs_with_blend_percentages": sum(bool(s.grape_constraints) for s in self.specs),
            "legal_specs_with_yield_limits": sum(s.max_yield_t_ha is not None for s in self.specs),
            "legal_specs_with_wine_yield_limits": sum(s.max_yield_hl_ha is not None for s in self.specs),
            "legal_specs_with_grape_to_wine_yield_limits": sum(s.grape_to_wine_yield_pct is not None for s in self.specs),
            "legal_specs_with_must_sugar_rules": sum(s.min_must_sugar_g_l is not None for s in self.specs),
            "legal_specs_with_potential_alcohol_rules": sum(s.min_potential_alcohol_pct is not None for s in self.specs),
            "legal_specs_with_max_total_alcohol_rules": sum(s.max_total_alcohol_pct is not None for s in self.specs),
            "legal_specs_with_bottling_origin_rules": sum(s.bottling_in_origin_required for s in self.specs),
            "legal_specs_with_residual_sugar_limits": sum(s.max_residual_sugar_g_l is not None for s in self.specs),
            "legal_specs_with_malic_acid_limits": sum(s.max_malic_acid_g_l is not None for s in self.specs),
            "legal_specs_with_aging_rules": sum(
                s.min_total_aging_months is not None
                or s.min_wood_aging_months is not None
                or s.min_bottle_aging_months is not None
                or s.min_elevage_until_month is not None
                for s in self.specs
            ),
            "legal_specs_with_exact_elevage_dates": sum(s.min_elevage_until_month is not None for s in self.specs),
            "legal_specs_with_release_year_rules": sum(s.release_year_offset is not None for s in self.specs),
            "legal_specs_with_exact_release_dates": sum(s.earliest_release_month is not None for s in self.specs),
        }
