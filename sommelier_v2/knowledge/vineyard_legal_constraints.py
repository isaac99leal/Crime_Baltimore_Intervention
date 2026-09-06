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


@dataclass(frozen=True)
class VineyardLegalConstraint:
    id: str
    country: str
    appellation: str
    min_vine_density_per_ha: int | None = None
    irrigation_prohibited: bool | None = None
    variants: tuple[str, ...] = ()
    effective_from: str | None = None
    effective_to: str | None = None
    source_ids: tuple[str, ...] = ()
    notes: str = ""


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
                    raise ValueError(
                        f"{constraint_id} references unknown legal sources: {unknown}"
                    )

                density_raw = raw.get("min_vine_density_per_ha")
                density = None if density_raw is None else int(density_raw)
                if density is not None and not 100 <= density <= 30000:
                    raise ValueError(
                        f"{constraint_id} has unsupported minimum vine density: {density}"
                    )

                irrigation_raw = raw.get("irrigation_prohibited")
                if irrigation_raw is not None and not isinstance(irrigation_raw, bool):
                    raise ValueError(
                        f"{constraint_id} irrigation_prohibited must be boolean or null"
                    )

                constraint = VineyardLegalConstraint(
                    id=constraint_id,
                    country=str(raw["country"]),
                    appellation=str(raw["appellation"]),
                    min_vine_density_per_ha=density,
                    irrigation_prohibited=irrigation_raw,
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
        candidates = self._index.get(
            (normalize_name(country), normalize_name(appellation)),
            [],
        )
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
                unresolved.append(
                    "Irrigation amount is required to assess the reviewed irrigation prohibition."
                )
            elif irrigation_mm_per_week > 1e-9:
                issues.append(
                    f"Irrigation is prohibited for sourced {constraint.appellation} vineyard eligibility; configured irrigation is {irrigation_mm_per_week:g} mm/week."
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
            "vineyard_density_constraints": sum(
                row.min_vine_density_per_ha is not None for row in self.constraints
            ),
            "vineyard_irrigation_constraints": sum(
                row.irrigation_prohibited is not None for row in self.constraints
            ),
        }
