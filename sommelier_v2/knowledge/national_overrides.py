"""National-source precedence and cross-checks for strict wine specifications.

EU registry attachments remain valuable provenance.  When a current national
regulator publishes a newer consolidated rule or a more detailed national
requirement, this layer can confirm or replace specific executable fields. Draft
or opposition-stage changes are recorded but never applied as current law.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data" / "national_legal_overrides.json"

_ALLOWED_FIELDS = {
    "max_yield_t_ha",
    "grape_to_wine_yield_pct",
    "min_potential_alcohol_pct",
    "min_final_alcohol_pct",
    "min_total_acidity_g_l",
    "min_dry_extract_g_l",
    "min_total_aging_months",
    "min_wood_aging_months",
    "min_bottle_aging_months",
    "release_year_offset",
    "required_method",
    "manual_harvest_required",
    "bottling_in_origin_required",
    "vineyard_adaptation_max_pct",
}


@dataclass(frozen=True)
class NationalOverrideDecision:
    spec_id: str
    effective: bool
    status: str
    confirmed_fields: tuple[str, ...] = ()
    changed_fields: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


class NationalLegalOverrideRegistry:
    def __init__(self, data_path: Path | None = None) -> None:
        path = data_path or DATA_PATH
        doc = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.sources: dict[str, dict] = {
            str(key): dict(value) for key, value in doc.get("sources", {}).items()
        }
        self.records: list[dict] = []
        self.by_spec: dict[str, list[dict]] = {}
        for raw in doc.get("overrides", []):
            row = dict(raw)
            spec_id = str(row.get("spec_id") or "")
            if not spec_id:
                raise ValueError("National override is missing spec_id")
            unknown = set(row.get("fields", {})) - _ALLOWED_FIELDS
            if unknown:
                raise ValueError(
                    f"{spec_id} national override has unsupported fields: {sorted(unknown)}"
                )
            source_ids = tuple(row.get("source_ids", []))
            missing = [source_id for source_id in source_ids if source_id not in self.sources]
            if missing:
                raise ValueError(
                    f"{spec_id} national override references unknown sources: {missing}"
                )
            row["source_ids"] = source_ids
            self.records.append(row)
            self.by_spec.setdefault(spec_id, []).append(row)

    @staticmethod
    def _is_effective(row: dict) -> bool:
        return str(row.get("status", "effective")).casefold() in {
            "effective",
            "current",
            "in_force",
        }

    def decision(self, spec) -> NationalOverrideDecision:
        rows = self.by_spec.get(spec.id, [])
        if not rows:
            return NationalOverrideDecision(spec.id, False, "no_national_override")
        effective_rows = [row for row in rows if self._is_effective(row)]
        if not effective_rows:
            evidence = tuple(
                f"source:{source_id}"
                for row in rows
                for source_id in row.get("source_ids", ())
            )
            return NationalOverrideDecision(
                spec.id, False, "national_change_recorded_not_effective", evidence=evidence
            )
        confirmed: list[str] = []
        changed: list[str] = []
        evidence: list[str] = []
        current = spec
        for row in effective_rows:
            evidence.extend(f"source:{source_id}" for source_id in row["source_ids"])
            for field_name, value in row.get("fields", {}).items():
                if getattr(current, field_name) == value:
                    confirmed.append(field_name)
                else:
                    changed.append(field_name)
                    current = replace(current, **{field_name: value})
        return NationalOverrideDecision(
            spec.id,
            True,
            "national_override_or_crosscheck_applied",
            tuple(dict.fromkeys(confirmed)),
            tuple(dict.fromkeys(changed)),
            tuple(dict.fromkeys(evidence)),
        )

    def apply(self, spec):
        rows = [row for row in self.by_spec.get(spec.id, []) if self._is_effective(row)]
        if not rows:
            return spec
        updates: dict[str, object] = {}
        source_ids = list(spec.source_ids)
        notes = spec.notes
        for row in rows:
            updates.update(row.get("fields", {}))
            for source_id in row["source_ids"]:
                if source_id not in source_ids:
                    source_ids.append(source_id)
            note = str(row.get("notes", "")).strip()
            if note and note not in notes:
                notes = (notes + " " + note).strip()
        return replace(spec, **updates, source_ids=tuple(source_ids), notes=notes)

    def stats(self) -> dict[str, int]:
        effective = [row for row in self.records if self._is_effective(row)]
        pending = [row for row in self.records if not self._is_effective(row)]
        return {
            "national_legal_override_records": len(self.records),
            "national_legal_effective_records": len(effective),
            "national_legal_pending_records": len(pending),
            "national_legal_override_countries": len(
                {str(row.get("country", "")) for row in self.records if row.get("country")}
            ),
            "national_legal_executable_field_assertions": sum(
                len(row.get("fields", {})) for row in effective
            ),
        }


class NationalAwareLegalSpecRegistry:
    """Facade over LegalSpecRegistry that applies current national precedence."""

    def __init__(self, base_registry=None, *, override_registry: NationalLegalOverrideRegistry | None = None):
        if base_registry is None:
            from .legal_specs import LegalSpecRegistry
            base_registry = LegalSpecRegistry()
        self.base = base_registry
        self.overrides = override_registry or NationalLegalOverrideRegistry()
        self.sources = dict(getattr(self.base, "sources", {}))
        for source_id, source in self.overrides.sources.items():
            self.sources.setdefault(source_id, source)
        self.specs = [self.overrides.apply(spec) for spec in self.base.specs]

    def resolve(self, **kwargs):
        spec = self.base.resolve(**kwargs)
        return self.overrides.apply(spec) if spec is not None else None

    def evaluate_blend(self, spec, *args, **kwargs):
        return self.base.evaluate_blend(spec, *args, **kwargs)

    def validate_production(self, spec, *args, **kwargs):
        return self.base.validate_production(spec, *args, **kwargs)

    def validate_release(self, spec, *args, **kwargs):
        return self.base.validate_release(spec, *args, **kwargs)

    def stats(self) -> dict[str, int]:
        stats = self.base.stats()
        stats.update(self.overrides.stats())
        return stats
