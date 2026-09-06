"""Sourced vineyard-law constraints that are mechanically observable by the simulator.

This layer is intentionally separate from physical vineyard mechanics and from the
wine-production specification. A block can be agronomically simulated while
failing a protected-origin vineyard rule. Absence from this registry is never
interpreted as proof that no additional vineyard law exists.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .catalog import normalize_name
from .legal_specs import LegalSpecRegistry

DATA_DIR = Path(__file__).resolve().parent / "data"


def _token(value: str | None) -> str:
    return normalize_name(value or "").replace(" ", "_")


@dataclass(frozen=True)
class VineyardLegalConstraint:
    id: str
    country: str
    appellation: str
    min_vine_density_per_ha: int | None = None
    irrigation_prohibited: bool | None = None
    allowed_planting_patterns: tuple[str, ...] = ()
    max_row_spacing_m: float | None = None
    min_vine_spacing_m: float | None = None
    min_foule_vine_spacing_m_exclusive: float | None = None
    pruning_max_buds: tuple[tuple[str, str, int], ...] = ()
    pruning_unmodeled_exception_systems: tuple[str, ...] = ()
    allowed_support_systems_unless_gobelet: tuple[str, ...] = ()
    required_support_for_foule: str | None = None
    min_trellised_canopy_height_to_row_spacing_ratio: float | None = None
    max_parcel_crop_load_kg_ha_by_style: tuple[tuple[str, float], ...] = ()
    variants: tuple[str, ...] = ()
    effective_from: str | None = None
    effective_to: str | None = None
    source_ids: tuple[str, ...] = ()
    notes: str = ""

    def pruning_rule_map(self, wine_style: str | None) -> dict[str, int]:
        style = _token(wine_style)
        return {
            system: max_buds
            for row_style, system, max_buds in self.pruning_max_buds
            if row_style == style
        }

    def crop_load_limit(self, wine_style: str | None) -> float | None:
        style = _token(wine_style)
        for row_style, value in self.max_parcel_crop_load_kg_ha_by_style:
            if row_style == style:
                return value
        return None


@dataclass(frozen=True)
class VineyardLegalAssessment:
    """Tri-state assessment of the vineyard-law fields this registry can observe."""

    satisfied: bool | None
    status: str
    constraint_id: str | None = None
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


class VineyardLegalConstraintRegistry:
    """Load reviewed, machine-observable vineyard-law constraints.

    A missing constraint produces ``satisfied=None`` rather than True. This registry
    therefore cannot turn incomplete legal research into positive authorization.
    """

    def __init__(self, *, legal_specs: LegalSpecRegistry | None = None) -> None:
        self.legal_specs = legal_specs or LegalSpecRegistry()
        self.constraints: list[VineyardLegalConstraint] = []
        self._index: dict[tuple[str, str], list[VineyardLegalConstraint]] = {}

        seen_ids: set[str] = set()
        for path in sorted(DATA_DIR.glob("vineyard_legal_constraints_*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise ValueError(f"{path.name} must contain a JSON object")
            for raw in doc.get("constraints", []):
                if not isinstance(raw, dict):
                    continue
                constraint_id = str(raw.get("id") or "")
                if not constraint_id:
                    raise ValueError(f"{path.name} contains a vineyard constraint without an id")
                if constraint_id in seen_ids:
                    raise ValueError(f"Duplicate vineyard legal constraint id: {constraint_id}")
                seen_ids.add(constraint_id)

                source_ids = tuple(str(value) for value in raw.get("source_ids", []))
                unknown = [source_id for source_id in source_ids if source_id not in self.legal_specs.sources]
                if unknown:
                    raise ValueError(f"{constraint_id} references unknown legal sources: {unknown}")

                density_raw = raw.get("min_vine_density_per_ha")
                density = None if density_raw is None else int(density_raw)
                if density is not None and not 100 <= density <= 30000:
                    raise ValueError(f"{constraint_id} has unsupported minimum vine density: {density}")

                irrigation_raw = raw.get("irrigation_prohibited")
                if irrigation_raw is not None and not isinstance(irrigation_raw, bool):
                    raise ValueError(f"{constraint_id} irrigation_prohibited must be boolean or null")

                patterns = tuple(_token(str(value)) for value in raw.get("allowed_planting_patterns", []))
                if any(value not in {"rows", "foule"} for value in patterns):
                    raise ValueError(f"{constraint_id} has unsupported planting patterns: {patterns}")

                max_row_spacing_raw = raw.get("max_row_spacing_m")
                max_row_spacing = None if max_row_spacing_raw is None else float(max_row_spacing_raw)
                if max_row_spacing is not None and not 0.3 <= max_row_spacing <= 6.0:
                    raise ValueError(f"{constraint_id} has unsupported maximum row spacing: {max_row_spacing}")

                min_vine_spacing_raw = raw.get("min_vine_spacing_m")
                min_vine_spacing = None if min_vine_spacing_raw is None else float(min_vine_spacing_raw)
                if min_vine_spacing is not None and not 0.2 <= min_vine_spacing <= 6.0:
                    raise ValueError(f"{constraint_id} has unsupported minimum vine spacing: {min_vine_spacing}")

                foule_spacing_raw = raw.get("min_foule_vine_spacing_m_exclusive")
                foule_spacing = None if foule_spacing_raw is None else float(foule_spacing_raw)
                if foule_spacing is not None and not 0.2 <= foule_spacing <= 6.0:
                    raise ValueError(f"{constraint_id} has unsupported foule vine spacing: {foule_spacing}")

                pruning_rows: list[tuple[str, str, int]] = []
                pruning_raw = raw.get("pruning_max_buds_by_style_and_system", {})
                if not isinstance(pruning_raw, dict):
                    raise ValueError(f"{constraint_id} pruning rules must be an object")
                for raw_style, raw_systems in pruning_raw.items():
                    style = _token(str(raw_style))
                    if style not in {"red", "white", "rose"} or not isinstance(raw_systems, dict):
                        raise ValueError(f"{constraint_id} has invalid pruning style: {raw_style}")
                    for raw_system, raw_max_buds in raw_systems.items():
                        system = _token(str(raw_system))
                        max_buds = int(raw_max_buds)
                        if not system or not 1 <= max_buds <= 100:
                            raise ValueError(
                                f"{constraint_id} has invalid pruning rule {raw_style}/{raw_system}: {raw_max_buds}"
                            )
                        pruning_rows.append((style, system, max_buds))

                pruning_exceptions = tuple(
                    _token(str(value))
                    for value in raw.get("pruning_unmodeled_exception_systems", [])
                )

                allowed_support = tuple(
                    _token(str(value))
                    for value in raw.get("allowed_support_systems_unless_gobelet", [])
                )
                if any(value not in {"trellis", "stake"} for value in allowed_support):
                    raise ValueError(f"{constraint_id} has unsupported support systems: {allowed_support}")

                required_foule_support_raw = raw.get("required_support_for_foule")
                required_foule_support = (
                    _token(str(required_foule_support_raw))
                    if required_foule_support_raw is not None
                    else None
                )
                if required_foule_support not in {None, "trellis", "stake"}:
                    raise ValueError(f"{constraint_id} has unsupported foule support: {required_foule_support}")

                canopy_ratio_raw = raw.get("min_trellised_canopy_height_to_row_spacing_ratio")
                canopy_ratio = None if canopy_ratio_raw is None else float(canopy_ratio_raw)
                if canopy_ratio is not None and not 0.1 <= canopy_ratio <= 3.0:
                    raise ValueError(f"{constraint_id} has unsupported canopy-height ratio: {canopy_ratio}")

                crop_load_rows: list[tuple[str, float]] = []
                crop_load_raw = raw.get("max_parcel_crop_load_kg_ha_by_style", {})
                if not isinstance(crop_load_raw, dict):
                    raise ValueError(f"{constraint_id} crop-load rules must be an object")
                for raw_style, raw_limit in crop_load_raw.items():
                    style = _token(str(raw_style))
                    limit = float(raw_limit)
                    if style not in {"red", "white", "rose"} or not 0 < limit <= 100000:
                        raise ValueError(
                            f"{constraint_id} has invalid parcel crop-load rule: {raw_style}={raw_limit}"
                        )
                    crop_load_rows.append((style, limit))

                constraint = VineyardLegalConstraint(
                    id=constraint_id,
                    country=str(raw["country"]),
                    appellation=str(raw["appellation"]),
                    min_vine_density_per_ha=density,
                    irrigation_prohibited=irrigation_raw,
                    allowed_planting_patterns=patterns,
                    max_row_spacing_m=max_row_spacing,
                    min_vine_spacing_m=min_vine_spacing,
                    min_foule_vine_spacing_m_exclusive=foule_spacing,
                    pruning_max_buds=tuple(pruning_rows),
                    pruning_unmodeled_exception_systems=pruning_exceptions,
                    allowed_support_systems_unless_gobelet=allowed_support,
                    required_support_for_foule=required_foule_support,
                    min_trellised_canopy_height_to_row_spacing_ratio=canopy_ratio,
                    max_parcel_crop_load_kg_ha_by_style=tuple(crop_load_rows),
                    variants=tuple(str(value) for value in raw.get("variants", [])),
                    effective_from=str(raw["effective_from"]) if raw.get("effective_from") else None,
                    effective_to=str(raw["effective_to"]) if raw.get("effective_to") else None,
                    source_ids=source_ids,
                    notes=str(raw.get("notes", "")),
                )
                self.constraints.append(constraint)
                key = (normalize_name(constraint.country), normalize_name(constraint.appellation))
                self._index.setdefault(key, []).append(constraint)

    def resolve(
        self,
        *,
        country: str,
        appellation: str,
        variant: str | None = None,
    ) -> VineyardLegalConstraint | None:
        candidates = self._index.get((normalize_name(country), normalize_name(appellation)), [])
        if not candidates:
            return None
        variant_key = normalize_name(variant or "")
        exact = [
            row
            for row in candidates
            if row.variants and variant_key in {normalize_name(value) for value in row.variants}
        ]
        if exact:
            return exact[0]
        general = [row for row in candidates if not row.variants]
        return general[0] if general else None

    def assess(
        self,
        *,
        country: str,
        appellation: str,
        vine_density_per_ha: int | None,
        irrigation_mm_per_week: float | None = None,
        planting_pattern: str | None = None,
        row_spacing_m: float | None = None,
        vine_spacing_m: float | None = None,
        wine_style: str | None = None,
        pruning_system: str | None = None,
        retained_buds_per_vine: int | None = None,
        fruiting_shoots_per_vine: int | None = None,
        support_system: str | None = None,
        canopy_height_m: float | None = None,
        parcel_crop_load_kg_ha: float | None = None,
        variant: str | None = None,
    ) -> VineyardLegalAssessment:
        constraint = self.resolve(country=country, appellation=appellation, variant=variant)
        if constraint is None:
            return VineyardLegalAssessment(
                satisfied=None,
                status="vineyard_law_not_reviewed",
                warnings=(
                    "No machine-observable vineyard-law constraint has been reviewed for this origin; absence is not permission.",
                ),
            )

        evidence = tuple(f"source:{source_id}" for source_id in constraint.source_ids)
        issues: list[str] = []
        unresolved: list[str] = []

        if constraint.min_vine_density_per_ha is not None:
            if vine_density_per_ha is None:
                unresolved.append("Vine density is required to assess the reviewed vineyard-law minimum.")
            elif vine_density_per_ha < constraint.min_vine_density_per_ha:
                issues.append(
                    f"Vine density {vine_density_per_ha:,} vines/ha is below the sourced {constraint.appellation} minimum of {constraint.min_vine_density_per_ha:,} vines/ha."
                )

        if constraint.irrigation_prohibited is True:
            if irrigation_mm_per_week is None:
                unresolved.append("Irrigation amount is required to assess the reviewed irrigation prohibition.")
            elif irrigation_mm_per_week > 1e-9:
                issues.append(
                    f"Irrigation is prohibited for sourced {constraint.appellation} vineyard eligibility; configured irrigation is {irrigation_mm_per_week:g} mm/week."
                )

        pattern_key = _token(planting_pattern) if planting_pattern is not None else None
        if constraint.allowed_planting_patterns:
            if pattern_key is None:
                unresolved.append("Planting pattern is required to assess the reviewed row/foule vineyard geometry.")
            elif pattern_key not in constraint.allowed_planting_patterns:
                issues.append(
                    f"Planting pattern {planting_pattern!r} is not among the reviewed {constraint.appellation} patterns {constraint.allowed_planting_patterns}."
                )

        if constraint.max_row_spacing_m is not None and pattern_key == "rows":
            if row_spacing_m is None:
                unresolved.append("Row spacing is required for a conventionally row-planted parcel.")
            elif row_spacing_m > constraint.max_row_spacing_m + 1e-9:
                issues.append(
                    f"Row spacing {row_spacing_m:g} m exceeds the sourced {constraint.appellation} maximum of {constraint.max_row_spacing_m:g} m."
                )

        if vine_spacing_m is None and (
            constraint.min_vine_spacing_m is not None
            or constraint.min_foule_vine_spacing_m_exclusive is not None
        ):
            unresolved.append("Vine-to-vine spacing is required to assess the reviewed vineyard geometry.")
        elif vine_spacing_m is not None:
            if pattern_key == "foule" and constraint.min_foule_vine_spacing_m_exclusive is not None:
                if vine_spacing_m <= constraint.min_foule_vine_spacing_m_exclusive + 1e-12:
                    issues.append(
                        f"Foule vine spacing {vine_spacing_m:g} m must be strictly greater than the sourced {constraint.appellation} threshold of {constraint.min_foule_vine_spacing_m_exclusive:g} m."
                    )
            elif constraint.min_vine_spacing_m is not None and vine_spacing_m + 1e-9 < constraint.min_vine_spacing_m:
                issues.append(
                    f"Vine spacing {vine_spacing_m:g} m is below the sourced {constraint.appellation} minimum of {constraint.min_vine_spacing_m:g} m."
                )

        style_key = _token(wine_style) if wine_style is not None else None
        pruning_key = _token(pruning_system) if pruning_system is not None else None
        if constraint.pruning_max_buds:
            if style_key is None:
                unresolved.append("Wine color/style is required to assess the reviewed pruning rule.")
            else:
                style_pruning = constraint.pruning_rule_map(style_key)
                if not style_pruning:
                    unresolved.append(f"No reviewed pruning matrix is encoded for wine style {wine_style!r}.")
                elif pruning_key is None:
                    unresolved.append("Pruning system is required to assess the reviewed pruning rule.")
                elif pruning_key in constraint.pruning_unmodeled_exception_systems:
                    unresolved.append(
                        f"Pruning system {pruning_system!r} has a sourced conditional exception that requires additional parcel state and is not generalized."
                    )
                elif pruning_key not in style_pruning:
                    issues.append(
                        f"Pruning system {pruning_system!r} is not an encoded positive {style_key} pruning path for sourced {constraint.appellation}."
                    )
                else:
                    max_buds = style_pruning[pruning_key]
                    if retained_buds_per_vine is None:
                        unresolved.append("Retained buds per vine are required to assess the reviewed pruning ceiling.")
                    elif retained_buds_per_vine > max_buds:
                        if fruiting_shoots_per_vine is None:
                            unresolved.append(
                                f"{retained_buds_per_vine} retained buds exceed the ordinary {max_buds}-bud ceiling; a fruiting-shoot count at 11-12 leaves is required for the sourced conditional allowance."
                            )
                        elif fruiting_shoots_per_vine > max_buds:
                            issues.append(
                                f"Fruiting shoots {fruiting_shoots_per_vine} per vine exceed the sourced {constraint.appellation} {style_key} pruning ceiling of {max_buds}."
                            )

        support_key = _token(support_system) if support_system is not None else None
        if pattern_key == "foule" and constraint.required_support_for_foule:
            if support_key is None:
                unresolved.append("Support system is required for a foule-planted parcel.")
            elif support_key != constraint.required_support_for_foule:
                issues.append(
                    f"Foule-planted {constraint.appellation} vines require {constraint.required_support_for_foule}; configured support is {support_system!r}."
                )
        elif (
            pruning_key is not None
            and pruning_key != "gobelet"
            and pruning_key not in constraint.pruning_unmodeled_exception_systems
            and constraint.allowed_support_systems_unless_gobelet
        ):
            if support_key is None:
                unresolved.append("Support system is required for a reviewed non-gobelet training path.")
            elif support_key not in constraint.allowed_support_systems_unless_gobelet:
                issues.append(
                    f"Non-gobelet {constraint.appellation} vines require one of {constraint.allowed_support_systems_unless_gobelet}; configured support is {support_system!r}."
                )

        if (
            constraint.min_trellised_canopy_height_to_row_spacing_ratio is not None
            and support_key == "trellis"
        ):
            if row_spacing_m is None:
                unresolved.append("Row spacing is required to calculate the reviewed trellised-canopy height minimum.")
            elif canopy_height_m is None:
                unresolved.append("Measured trellised canopy height is required to assess the reviewed canopy-height rule.")
            else:
                minimum_canopy = constraint.min_trellised_canopy_height_to_row_spacing_ratio * row_spacing_m
                if canopy_height_m + 1e-9 < minimum_canopy:
                    issues.append(
                        f"Trellised canopy height {canopy_height_m:g} m is below the sourced {constraint.appellation} minimum of {minimum_canopy:g} m for {row_spacing_m:g} m row spacing."
                    )

        if constraint.max_parcel_crop_load_kg_ha_by_style:
            if style_key is None:
                unresolved.append("Wine color/style is required to assess parcel crop load.")
            else:
                crop_limit = constraint.crop_load_limit(style_key)
                if crop_limit is None:
                    unresolved.append(f"No reviewed parcel crop-load ceiling is encoded for wine style {wine_style!r}.")
                elif parcel_crop_load_kg_ha is None:
                    unresolved.append("Measured parcel crop load is required to assess the reviewed load ceiling.")
                elif parcel_crop_load_kg_ha > crop_limit + 1e-9:
                    issues.append(
                        f"Parcel crop load {parcel_crop_load_kg_ha:g} kg/ha exceeds the sourced {constraint.appellation} {style_key} maximum of {crop_limit:g} kg/ha."
                    )

        if issues:
            return VineyardLegalAssessment(
                satisfied=False,
                status="reviewed_vineyard_constraint_violation",
                constraint_id=constraint.id,
                issues=tuple(issues),
                warnings=tuple(unresolved),
                evidence=evidence,
            )
        if unresolved:
            return VineyardLegalAssessment(
                satisfied=None,
                status="reviewed_vineyard_constraint_unobserved",
                constraint_id=constraint.id,
                warnings=tuple(unresolved),
                evidence=evidence,
            )
        return VineyardLegalAssessment(
            satisfied=True,
            status="reviewed_vineyard_constraints_satisfied",
            constraint_id=constraint.id,
            evidence=evidence,
        )

    def stats(self) -> dict[str, int]:
        return {
            "vineyard_legal_constraints": len(self.constraints),
            "vineyard_legal_origins": len(
                {(normalize_name(row.country), normalize_name(row.appellation)) for row in self.constraints}
            ),
            "vineyard_density_constraints": sum(row.min_vine_density_per_ha is not None for row in self.constraints),
            "vineyard_irrigation_constraints": sum(row.irrigation_prohibited is not None for row in self.constraints),
            "vineyard_planting_pattern_constraints": sum(bool(row.allowed_planting_patterns) for row in self.constraints),
            "vineyard_row_spacing_constraints": sum(row.max_row_spacing_m is not None for row in self.constraints),
            "vineyard_vine_spacing_constraints": sum(
                row.min_vine_spacing_m is not None or row.min_foule_vine_spacing_m_exclusive is not None
                for row in self.constraints
            ),
            "vineyard_pruning_constraints": sum(bool(row.pruning_max_buds) for row in self.constraints),
            "vineyard_support_constraints": sum(
                bool(row.allowed_support_systems_unless_gobelet) or row.required_support_for_foule is not None
                for row in self.constraints
            ),
            "vineyard_canopy_height_constraints": sum(
                row.min_trellised_canopy_height_to_row_spacing_ratio is not None
                for row in self.constraints
            ),
            "vineyard_parcel_crop_load_constraints": sum(
                bool(row.max_parcel_crop_load_kg_ha_by_style) for row in self.constraints
            ),
        }
