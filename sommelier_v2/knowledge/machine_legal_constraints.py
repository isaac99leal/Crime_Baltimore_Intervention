"""Deny-safe constraints extracted mechanically from authoritative legal specs.

A record at ``constraint_level='deny_only'`` can prove that a grape is outside a
bounded authorized-variety section. It cannot prove full appellation eligibility.
The strict legal registry remains the only source that can positively authorize a
protected-origin wine.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .catalog import normalize_name

DATA_PATH = Path(__file__).resolve().parent / "data" / "legal_spec_machine_constraints.json"

COUNTRY_TO_CODE = {
    "France": "FR", "Italy": "IT", "Spain": "ES", "Portugal": "PT",
    "Austria": "AT", "Slovenia": "SI", "Germany": "DE", "Greece": "GR",
    "Hungary": "HU",
}


@dataclass(frozen=True)
class MachineLegalConstraint:
    gi_identifier: str
    file_number: str
    protected_names: tuple[str, ...]
    countries: tuple[str, ...]
    gi_type: str | None
    allowed_grapes: tuple[str, ...]
    constraint_level: str
    extraction_status: str
    source_attachment_id: str | None
    source_url: str | None
    section_sha256: str | None

    @property
    def deny_safe(self) -> bool:
        return self.constraint_level == "deny_only" and bool(self.allowed_grapes)


@dataclass(frozen=True)
class MachineConstraintDecision:
    rejected: bool
    status: str
    record: MachineLegalConstraint | None = None
    issues: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


class MachineLegalConstraintRegistry:
    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or DATA_PATH
        self.records: list[MachineLegalConstraint] = []
        self._index: dict[tuple[str, str], list[MachineLegalConstraint]] = {}
        if not self.data_path.exists():
            return
        raw = json.loads(self.data_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("legal_spec_machine_constraints.json must contain a list")
        for row in raw:
            if not isinstance(row, dict):
                continue
            record = MachineLegalConstraint(
                gi_identifier=str(row.get("gi_identifier") or ""),
                file_number=str(row.get("file_number") or ""),
                protected_names=tuple(str(x) for x in row.get("protected_names", []) if str(x).strip()),
                countries=tuple(str(x) for x in row.get("countries", []) if str(x).strip()),
                gi_type=row.get("gi_type"),
                allowed_grapes=tuple(str(x) for x in row.get("allowed_grapes", []) if str(x).strip()),
                constraint_level=str(row.get("constraint_level") or "source_only"),
                extraction_status=str(row.get("extraction_status") or "unknown"),
                source_attachment_id=str(row.get("source_attachment_id")) if row.get("source_attachment_id") else None,
                source_url=str(row.get("source_url")) if row.get("source_url") else None,
                section_sha256=str(row.get("section_sha256")) if row.get("section_sha256") else None,
            )
            if not record.gi_identifier:
                continue
            self.records.append(record)
            for country in record.countries:
                for name in record.protected_names:
                    self._index.setdefault((normalize_name(country), normalize_name(name)), []).append(record)

    def resolve(self, *, country: str, appellation: str | None = None, region: str | None = None,
                sub_region: str | None = None, commune: str | None = None) -> MachineLegalConstraint | None:
        code = COUNTRY_TO_CODE.get(country, country)
        for name in (commune, appellation, sub_region, region):
            if not name:
                continue
            rows = self._index.get((normalize_name(code), normalize_name(name)), [])
            deny = [row for row in rows if row.deny_safe]
            if deny:
                return deny[0]
        return None

    @staticmethod
    def _grape_names(grapes: Mapping[str, float] | Sequence[str] | str) -> tuple[str, ...]:
        if isinstance(grapes, str):
            return (grapes,)
        if isinstance(grapes, Mapping):
            return tuple(str(name) for name in grapes)
        return tuple(str(name) for name in grapes)

    def evaluate_deny(
        self,
        record: MachineLegalConstraint,
        grapes: Mapping[str, float] | Sequence[str] | str,
        *,
        canonicalize: Callable[[str], str] = lambda value: value,
        same_grape: Callable[[str, str], bool] | None = None,
    ) -> MachineConstraintDecision:
        if not record.deny_safe:
            return MachineConstraintDecision(False, "machine_constraint_not_deny_safe", record)
        same = same_grape or (lambda a, b: normalize_name(a) == normalize_name(b))
        canonical = tuple(canonicalize(name) for name in self._grape_names(grapes))
        forbidden = tuple(
            grape for grape in canonical
            if not any(same(grape, allowed) for allowed in record.allowed_grapes)
        )
        if not forbidden:
            return MachineConstraintDecision(
                False, "machine_membership_pass_not_authorization", record,
                evidence=(f"eambrosia:{record.gi_identifier}", f"attachment:{record.source_attachment_id}"),
            )
        return MachineConstraintDecision(
            True,
            "grape_not_permitted_machine_extracted",
            record,
            issues=tuple(f"{grape} is outside the explicit authorized-variety section extracted for {record.protected_names[0] if record.protected_names else record.gi_identifier}" for grape in forbidden),
            evidence=(f"eambrosia:{record.gi_identifier}", f"attachment:{record.source_attachment_id}", f"section_sha256:{record.section_sha256}"),
        )

    def stats(self) -> dict[str, int]:
        deny = [record for record in self.records if record.deny_safe]
        countries = {country for record in deny for country in record.countries}
        return {
            "machine_legal_constraint_records": len(self.records),
            "machine_legal_deny_safe_records": len(deny),
            "machine_legal_deny_safe_countries": len(countries),
        }
