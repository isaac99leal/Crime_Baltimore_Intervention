"""Dynamic protected-origin yield adjustments driven by vineyard condition.

Some vineyard-law facts are not binary eligibility predicates. French Code rural
D.645-4 reduces the authorized AOC yield proportionally to the percentage of dead
or missing vines once an appellation-specific trigger is exceeded. This module
keeps that quantitative remedy separate from boolean vineyard-compliance
assessment and keeps trigger authority separate from remedy authority.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .catalog import normalize_name
from .legal_specs import LegalSpecRegistry

DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class VineyardYieldAdjustmentRule:
    id: str
    country: str
    appellation: str
    dead_missing_vine_threshold: float
    variants: tuple[str, ...] = ()
    threshold_source_ids: tuple[str, ...] = ()
    remedy_source_ids: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class VineyardYieldAdjustment:
    multiplier: float | None
    status: str
    rule_id: str | None = None
    threshold: float | None = None
    observed_dead_missing_fraction: float | None = None
    warnings: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


class VineyardYieldAdjustmentRegistry:
    """Load quantitative vineyard-law yield adjustments.

    ``multiplier=None`` means the reviewed adjustment cannot yet be evaluated. A
    multiplier of 1.0 means no reduction is triggered; values below 1.0 multiply
    the otherwise authorized protected-origin yield.
    """

    def __init__(self, *, legal_specs: LegalSpecRegistry | None = None) -> None:
        self.legal_specs = legal_specs or LegalSpecRegistry()
        self.sources: dict[str, dict] = {}
        self.rules: list[VineyardYieldAdjustmentRule] = []
        self._index: dict[tuple[str, str], list[VineyardYieldAdjustmentRule]] = {}
        seen: set[str] = set()

        documents: list[tuple[Path, dict]] = []
        for path in sorted(DATA_DIR.glob("vineyard_legal_constraints_*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise ValueError(f"{path.name} must contain a JSON object")
            documents.append((path, doc))
            for source_id, raw_source in doc.get("yield_adjustment_sources", {}).items():
                source_id = str(source_id)
                source = dict(raw_source)
                existing = self.sources.get(source_id)
                if existing is not None and existing != source:
                    raise ValueError(f"Conflicting vineyard yield-adjustment source: {source_id}")
                self.sources[source_id] = source

        for path, doc in documents:
            for raw in doc.get("constraints", []):
                if not isinstance(raw, dict):
                    continue
                threshold_raw = raw.get("dead_missing_vine_yield_reduction_threshold")
                if threshold_raw is None:
                    continue
                constraint_id = str(raw.get("id") or "")
                if not constraint_id:
                    raise ValueError(f"{path.name} contains a yield-adjustment rule without an id")
                rule_id = f"{constraint_id}:dead-missing-yield"
                if rule_id in seen:
                    raise ValueError(f"Duplicate vineyard yield-adjustment rule id: {rule_id}")
                seen.add(rule_id)

                threshold = float(threshold_raw)
                if not 0.0 <= threshold < 1.0:
                    raise ValueError(f"{rule_id} has invalid dead/missing-vine threshold: {threshold}")

                threshold_source_ids = tuple(
                    str(value) for value in raw.get("dead_missing_vine_threshold_source_ids", [])
                )
                remedy_source_ids = tuple(
                    str(value) for value in raw.get("dead_missing_vine_remedy_source_ids", [])
                )
                if not threshold_source_ids:
                    raise ValueError(f"{rule_id} is missing appellation threshold authority")
                if not remedy_source_ids:
                    raise ValueError(f"{rule_id} is missing quantitative remedy authority")

                unknown_threshold = [
                    source_id
                    for source_id in threshold_source_ids
                    if source_id not in self.legal_specs.sources
                ]
                if unknown_threshold:
                    raise ValueError(
                        f"{rule_id} references unknown appellation threshold sources: {unknown_threshold}"
                    )
                unknown_remedy = [
                    source_id for source_id in remedy_source_ids if source_id not in self.sources
                ]
                if unknown_remedy:
                    raise ValueError(
                        f"{rule_id} references unknown national remedy sources: {unknown_remedy}"
                    )

                rule = VineyardYieldAdjustmentRule(
                    id=rule_id,
                    country=str(raw["country"]),
                    appellation=str(raw["appellation"]),
                    dead_missing_vine_threshold=threshold,
                    variants=tuple(str(value) for value in raw.get("variants", [])),
                    threshold_source_ids=threshold_source_ids,
                    remedy_source_ids=remedy_source_ids,
                    notes=str(raw.get("notes", "")),
                )
                self.rules.append(rule)
                key = (normalize_name(rule.country), normalize_name(rule.appellation))
                self._index.setdefault(key, []).append(rule)

    def resolve(
        self,
        *,
        country: str,
        appellation: str,
        variant: str | None = None,
    ) -> VineyardYieldAdjustmentRule | None:
        rows = self._index.get((normalize_name(country), normalize_name(appellation)), [])
        if not rows:
            return None
        variant_key = normalize_name(variant or "")
        exact = [
            row for row in rows
            if row.variants and variant_key in {normalize_name(value) for value in row.variants}
        ]
        if exact:
            return exact[0]
        general = [row for row in rows if not row.variants]
        return general[0] if general else None

    def assess(
        self,
        *,
        country: str,
        appellation: str,
        dead_missing_vine_fraction: float | None,
        variant: str | None = None,
    ) -> VineyardYieldAdjustment:
        rule = self.resolve(country=country, appellation=appellation, variant=variant)
        if rule is None:
            return VineyardYieldAdjustment(
                multiplier=None,
                status="vineyard_yield_adjustment_not_reviewed",
            )

        evidence = tuple(
            [f"threshold-source:{source_id}" for source_id in rule.threshold_source_ids]
            + [f"remedy-source:{source_id}" for source_id in rule.remedy_source_ids]
        )
        if dead_missing_vine_fraction is None:
            return VineyardYieldAdjustment(
                multiplier=None,
                status="dead_missing_vine_fraction_unobserved",
                rule_id=rule.id,
                threshold=rule.dead_missing_vine_threshold,
                warnings=(
                    "Dead/missing-vine fraction is required to determine the reviewed protected-origin yield adjustment.",
                ),
                evidence=evidence,
            )
        if not 0.0 <= dead_missing_vine_fraction <= 1.0:
            raise ValueError("Dead/missing-vine fraction must be within 0..1")

        if dead_missing_vine_fraction <= rule.dead_missing_vine_threshold + 1e-12:
            return VineyardYieldAdjustment(
                multiplier=1.0,
                status="dead_missing_vine_reduction_not_triggered",
                rule_id=rule.id,
                threshold=rule.dead_missing_vine_threshold,
                observed_dead_missing_fraction=dead_missing_vine_fraction,
                evidence=evidence,
            )

        return VineyardYieldAdjustment(
            multiplier=max(0.0, 1.0 - dead_missing_vine_fraction),
            status="authorized_yield_reduced_for_dead_missing_vines",
            rule_id=rule.id,
            threshold=rule.dead_missing_vine_threshold,
            observed_dead_missing_fraction=dead_missing_vine_fraction,
            evidence=evidence,
        )

    def stats(self) -> dict[str, int]:
        return {
            "vineyard_yield_adjustment_rules": len(self.rules),
            "vineyard_yield_adjustment_origins": len(
                {(normalize_name(row.country), normalize_name(row.appellation)) for row in self.rules}
            ),
            "vineyard_yield_adjustment_sources": len(self.sources),
            "dead_missing_vine_yield_adjustment_rules": len(self.rules),
        }
