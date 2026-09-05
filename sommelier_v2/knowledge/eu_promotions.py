"""Verification ladder for machine-extracted EU wine legal constraints.

The eAmbrosia source index and machine parser intentionally separate evidence
levels. A bounded grape section can safely reject outsiders. A one-grape
authorized section can additionally prove the *composition dimension* for a
100% wine, but it still cannot certify all production/release requirements of
the protected designation.

Positive protected-origin eligibility remains the responsibility of
``LegalSpecRegistry`` until all mandatory dimensions have been verified.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Mapping, Sequence

from .catalog import normalize_name
from .machine_legal_constraints import (
    MachineLegalConstraint,
    MachineLegalConstraintRegistry,
)


class VerificationLevel(IntEnum):
    SOURCE_ONLY = 0
    DENY_SAFE = 1
    COMPOSITION_VERIFIED = 2
    FULLY_VERIFIED = 3


@dataclass(frozen=True)
class EuCompositionDecision:
    verified: bool
    level: VerificationLevel
    status: str
    record: MachineLegalConstraint | None = None
    canonical_grapes: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


class EuLegalPromotionRegistry:
    """Promote only facts that are logically complete at the claimed level."""

    def __init__(
        self,
        machine_constraints: MachineLegalConstraintRegistry | None = None,
    ) -> None:
        self.machine_constraints = machine_constraints or MachineLegalConstraintRegistry()

    @staticmethod
    def level(record: MachineLegalConstraint) -> VerificationLevel:
        if not record.deny_safe:
            return VerificationLevel.SOURCE_ONLY
        # A bounded list with exactly one legal grape proves the entire
        # grape-composition dimension for the 100% single-variety path.
        if len(record.allowed_grapes) == 1:
            return VerificationLevel.COMPOSITION_VERIFIED
        return VerificationLevel.DENY_SAFE

    def resolve(
        self,
        *,
        country: str,
        appellation: str | None = None,
        region: str | None = None,
        sub_region: str | None = None,
        commune: str | None = None,
    ) -> MachineLegalConstraint | None:
        return self.machine_constraints.resolve(
            country=country,
            appellation=appellation,
            region=region,
            sub_region=sub_region,
            commune=commune,
        )

    @staticmethod
    def _blend_rows(
        grapes: Mapping[str, float] | Sequence[str] | str,
    ) -> tuple[list[tuple[str, float | None]], list[str]]:
        issues: list[str] = []
        if isinstance(grapes, str):
            return [(grapes, 100.0)], issues
        if isinstance(grapes, Mapping):
            rows: list[tuple[str, float | None]] = []
            total = 0.0
            for name, pct in grapes.items():
                try:
                    value = float(pct)
                except (TypeError, ValueError):
                    issues.append(f"Invalid blend percentage for {name!r}")
                    continue
                if value <= 0 or value > 100:
                    issues.append(f"Blend percentage for {name!r} must be >0 and <=100")
                total += value
                rows.append((str(name), value))
            if rows and abs(total - 100.0) > 0.25:
                issues.append(f"Blend percentages must sum to 100 (got {total:.2f})")
            if not rows:
                issues.append("At least one grape is required")
            return rows, issues
        values = [str(value) for value in grapes]
        if not values:
            return [], ["At least one grape is required"]
        if len(values) == 1:
            return [(values[0], 100.0)], issues
        return [(value, None) for value in values], issues

    def evaluate_composition(
        self,
        record: MachineLegalConstraint,
        grapes: Mapping[str, float] | Sequence[str] | str,
        *,
        canonicalize: Callable[[str], str] = lambda value: value,
        same_grape: Callable[[str, str], bool] | None = None,
    ) -> EuCompositionDecision:
        level = self.level(record)
        same = same_grape or (lambda a, b: normalize_name(a) == normalize_name(b))
        rows, issues = self._blend_rows(grapes)
        canonical = tuple(canonicalize(name) for name, _ in rows)
        evidence = tuple(
            item for item in (
                f"eambrosia:{record.gi_identifier}" if record.gi_identifier else None,
                f"attachment:{record.source_attachment_id}" if record.source_attachment_id else None,
                f"section_sha256:{record.section_sha256}" if record.section_sha256 else None,
            )
            if item is not None
        )

        if issues:
            return EuCompositionDecision(
                False, level, "invalid_blend", record, canonical, tuple(issues), evidence
            )

        if level < VerificationLevel.COMPOSITION_VERIFIED:
            return EuCompositionDecision(
                False,
                level,
                "composition_not_complete_enough_to_promote",
                record,
                canonical,
                (
                    "The extracted authorized-variety section does not prove all "
                    "blend-percentage constraints.",
                ),
                evidence,
            )

        allowed = record.allowed_grapes[0]
        if any(not same(name, allowed) for name in canonical):
            return EuCompositionDecision(
                False,
                level,
                "grape_not_permitted_machine_extracted",
                record,
                canonical,
                tuple(
                    f"{name} is not the sole authorized grape in the extracted section"
                    for name in canonical
                    if not same(name, allowed)
                ),
                evidence,
            )

        if any(pct is None for _, pct in rows):
            return EuCompositionDecision(
                False,
                level,
                "explicit_percentages_required_for_composition_verification",
                record,
                canonical,
                ("A multi-row blend requires explicit percentages.",),
                evidence,
            )

        # Since every positive-volume row is the sole authorized grape and the
        # validated blend totals 100%, the grape-composition dimension is proven.
        return EuCompositionDecision(
            True,
            VerificationLevel.COMPOSITION_VERIFIED,
            "composition_verified_full_spec_pending",
            record,
            canonical,
            (),
            evidence,
        )

    def stats(self) -> dict[str, int]:
        levels = [self.level(record) for record in self.machine_constraints.records]
        promoted = [
            record
            for record in self.machine_constraints.records
            if self.level(record) >= VerificationLevel.COMPOSITION_VERIFIED
        ]
        countries = {country for record in promoted for country in record.countries}
        return {
            "eu_machine_source_records": len(levels),
            "eu_machine_deny_safe_or_better": sum(
                level >= VerificationLevel.DENY_SAFE for level in levels
            ),
            "eu_machine_composition_verified_records": len(promoted),
            "eu_machine_composition_verified_countries": len(countries),
        }
