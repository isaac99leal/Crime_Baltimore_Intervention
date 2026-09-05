"""Finished-wine assembly with provenance-backed New World label validation.

A proposed WineRecord does not become a ValidatedWineRecord until its physical
blend components, protected-origin names, variety claims and vintage claims pass
the jurisdiction-specific U.S./Australia/New Zealand rules.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Sequence

from ..domain import WineRecord
from .catalog import normalize_name
from .expanded_catalog import WorldWineKnowledgeCatalog
from .jurisdiction_labels import BlendComponent, JurisdictionLabelValidator, LabelClaimDecision, LabelClaims

DATA_DIR = Path(__file__).resolve().parent / "data"
_JURISDICTION_COUNTRY = {
    "us": "United States", "usa": "United States", "united states": "United States",
    "au": "Australia", "australia": "Australia",
    "nz": "New Zealand", "new zealand": "New Zealand",
}


class FinishedWineConstraintError(ValueError):
    """Raised when a proposed finished wine cannot legally carry its claims."""


@dataclass(frozen=True)
class ValidatedWineRecord(WineRecord):
    """WineRecord plus the immutable evidence used to construct its label."""
    provenance_components: tuple[BlendComponent, ...] = ()
    label_claims: LabelClaims | None = None
    label_validation_status: str = ""
    label_validation_evidence: tuple[str, ...] = ()
    provenance_fingerprint: str = ""
    front_label_lines: tuple[str, ...] = ()

    @property
    def front_label_text(self) -> str:
        return "\n".join(self.front_label_lines)


def _registry_source_lines(path: Path) -> tuple[str, ...]:
    if not path.exists():
        return ()
    return tuple(line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.lstrip().startswith("#"))


def _registry_tokens(path: Path) -> set[str]:
    tokens: set[str] = set()
    for line in _registry_source_lines(path):
        candidates = [line]
        candidates.extend(part.strip() for part in line.split(" / ") if part.strip())
        match = re.fullmatch(r"\s*(.*?)\s*\((.*?)\)\s*", line)
        if match:
            candidates.extend([match.group(1).strip(), match.group(2).strip()])
        tokens.update(normalize_name(value) for value in candidates if normalize_name(value))
    return tokens


def _key(value: str) -> str:
    return normalize_name(value)


class FinishedWineAssembler:
    """Construct commercial wine records from one physical provenance ledger."""

    def __init__(self, *, catalog: WorldWineKnowledgeCatalog | None = None,
                 validator: JurisdictionLabelValidator | None = None) -> None:
        self.catalog = catalog or WorldWineKnowledgeCatalog()
        self.validator = validator or JurisdictionLabelValidator()
        self.us_avas = _registry_tokens(DATA_DIR / "us_avas.txt")
        self.au_gis = _registry_tokens(DATA_DIR / "australia_gis.txt")
        self.nz_gis = _registry_tokens(DATA_DIR / "new_zealand_wine_gis.txt")

    def _canonical_grape(self, name: str) -> str:
        grape = self.catalog.grape(name)
        if grape is None:
            raise FinishedWineConstraintError(
                f"Unknown grape identity {name!r}; commercial assembly requires a catalogued identity."
            )
        return grape.name

    def _canonical_components(self, components: Sequence[BlendComponent]) -> tuple[BlendComponent, ...]:
        return tuple(replace(c, grape=self._canonical_grape(c.grape)) for c in components)

    def _canonical_claims(self, claims: LabelClaims) -> LabelClaims:
        return replace(claims, variety_names=tuple(self._canonical_grape(n) for n in claims.variety_names))

    def _registry_issues(self, claims: LabelClaims) -> list[str]:
        issues: list[str] = []
        jurisdiction = _key(claims.jurisdiction)
        origin_type = _key(claims.origin_type or "")
        if jurisdiction in {"us", "usa", "united states"} and origin_type in {"ava", "american viticultural area"}:
            for name in claims.origin_names:
                if _key(name) not in self.us_avas:
                    issues.append(f"{name} is not in the current TTB established-AVA snapshot.")
        if jurisdiction in {"au", "australia"}:
            for name in claims.origin_names:
                if _key(name) not in self.au_gis:
                    issues.append(f"{name} is not in the current Wine Australia protected-GI snapshot.")
        if jurisdiction in {"nz", "new zealand"} and claims.registered_nz_gi:
            for name in claims.origin_names:
                if _key(name) not in self.nz_gis:
                    issues.append(f"{name} is not in the current IPONZ registered wine-GI snapshot.")
        return issues

    @staticmethod
    def _fingerprint(components: Sequence[BlendComponent]) -> str:
        payload = [{"volume_pct": round(float(c.volume_pct), 8), "grape": c.grape,
                    "country": c.country, "origins": list(c.origins), "vintage": c.vintage}
                   for c in components]
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _share_grape(components: Sequence[BlendComponent], grape: str) -> float:
        key = _key(grape)
        return sum(c.volume_pct for c in components if _key(c.grape) == key)

    @staticmethod
    def _share_origin(components: Sequence[BlendComponent], origin: str) -> float:
        key = _key(origin)
        return sum(c.volume_pct for c in components
                   if _key(c.country) == key or any(_key(x) == key for x in c.origins))

    @staticmethod
    def _actual_grapes(components: Sequence[BlendComponent]) -> tuple[str, ...]:
        shares: dict[str, float] = {}
        display: dict[str, str] = {}
        for c in components:
            key = _key(c.grape)
            shares[key] = shares.get(key, 0.0) + c.volume_pct
            display.setdefault(key, c.grape)
        return tuple(display[key] for key, _ in sorted(
            shares.items(), key=lambda item: (-item[1], display[item[0]].casefold())))

    def _front_label_lines(self, prototype: WineRecord, components: Sequence[BlendComponent],
                           canonical_claims: LabelClaims, display_claims: LabelClaims) -> tuple[str, ...]:
        lines = [prototype.producer]
        if prototype.label and _key(prototype.label) != _key(prototype.producer):
            lines.append(prototype.label)
        if display_claims.vintage_years:
            lines.append(" / ".join(str(y) for y in display_claims.vintage_years))
        if display_claims.variety_names:
            if display_claims.shown_variety_percentages:
                parts = [f"{self._share_grape(components, canonical):g}% {shown}"
                         for shown, canonical in zip(display_claims.variety_names,
                                                     canonical_claims.variety_names)]
                lines.append(" · ".join(parts))
            else:
                lines.append(" · ".join(display_claims.variety_names))
        if display_claims.origin_names:
            if display_claims.shown_origin_percentages:
                lines.append(" · ".join(f"{self._share_origin(components, name):g}% {name}"
                                        for name in display_claims.origin_names))
            else:
                lines.append(" · ".join(display_claims.origin_names))
        return tuple(line for line in lines if line)

    def _prototype_issues(self, prototype: WineRecord, claims: LabelClaims) -> list[str]:
        issues: list[str] = []
        canonical_country = _JURISDICTION_COUNTRY.get(_key(claims.jurisdiction))
        if canonical_country is None:
            return [f"Unsupported finished-wine jurisdiction {claims.jurisdiction!r}."]
        if prototype.country and _key(prototype.country) != _key(canonical_country):
            issues.append(f"Prototype country {prototype.country!r} conflicts with {canonical_country} label jurisdiction.")
        if len(claims.origin_names) == 1 and prototype.appellation and _key(prototype.appellation) != _key(claims.origin_names[0]):
            issues.append(f"Prototype appellation {prototype.appellation!r} conflicts with label origin {claims.origin_names[0]!r}.")
        if len(claims.vintage_years) == 1 and prototype.vintage and prototype.vintage != claims.vintage_years[0]:
            issues.append(f"Prototype vintage {prototype.vintage} conflicts with label vintage {claims.vintage_years[0]}.")
        return issues

    def assemble(self, prototype: WineRecord, *, components: Sequence[BlendComponent],
                 claims: LabelClaims) -> ValidatedWineRecord:
        issues = self._prototype_issues(prototype, claims)
        if issues:
            raise FinishedWineConstraintError("; ".join(issues))
        canonical_components = self._canonical_components(components)
        canonical_claims = self._canonical_claims(claims)
        issues = self._registry_issues(claims)
        if issues:
            raise FinishedWineConstraintError("; ".join(issues))
        decision = self.validator.validate(canonical_components, canonical_claims)
        if not decision.eligible:
            raise FinishedWineConstraintError("; ".join(decision.issues) or decision.status)

        values = {field.name: getattr(prototype, field.name) for field in fields(WineRecord)}
        values["country"] = _JURISDICTION_COUNTRY[_key(claims.jurisdiction)]
        values["grapes"] = self._actual_grapes(canonical_components)
        if len(claims.origin_names) == 1:
            values["appellation"] = claims.origin_names[0]
            if not values["region"]:
                values["region"] = claims.origin_names[0]
        if len(claims.vintage_years) == 1:
            values["vintage"] = claims.vintage_years[0]
        elif len(claims.vintage_years) > 1:
            values["vintage"] = 0

        return ValidatedWineRecord(
            **values,
            provenance_components=canonical_components,
            label_claims=claims,
            label_validation_status=decision.status,
            label_validation_evidence=decision.evidence,
            provenance_fingerprint=self._fingerprint(canonical_components),
            front_label_lines=self._front_label_lines(prototype, canonical_components,
                                                      canonical_claims, claims),
        )

    def validate_existing(self, record: ValidatedWineRecord) -> LabelClaimDecision:
        if record.label_claims is None or not record.provenance_components:
            return LabelClaimDecision(False, "missing_finished_wine_provenance",
                                      ("Validated wine record is missing claims or provenance components.",))
        if self._fingerprint(record.provenance_components) != record.provenance_fingerprint:
            return LabelClaimDecision(False, "provenance_fingerprint_mismatch",
                                      ("Stored provenance ledger changed after label validation.",))
        issues = self._registry_issues(record.label_claims)
        if issues:
            return LabelClaimDecision(False, "protected_origin_registry_mismatch", tuple(issues))
        return self.validator.validate(record.provenance_components,
                                       self._canonical_claims(record.label_claims))

    def stats(self) -> dict[str, int]:
        return {
            "finished_wine_label_assembly_jurisdictions": 3,
            "finished_wine_ttb_ava_registry_rows": len(_registry_source_lines(DATA_DIR / "us_avas.txt")),
            "finished_wine_australia_gi_registry_rows": len(_registry_source_lines(DATA_DIR / "australia_gis.txt")),
            "finished_wine_nz_gi_registry_rows": len(_registry_source_lines(DATA_DIR / "new_zealand_wine_gis.txt")),
        }
