"""Evidence-reviewed botanical identity links; never an appellation permit.

Names folded for search only produce R2 candidates. An R4/R5 link requires a
reviewed, source-specific assertion, not merely a matching catalogue title.
The source assertion remains distinct from the legacy GrapeKnowledge profile.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import unicodedata

from .catalog import normalize_name

DATA_PATH = Path(__file__).resolve().parent / "data" / "variety_identity_evidence.json"
LEVELS = frozenset({"R0", "R1", "R2", "R3", "R4", "R5"})


def exact_name(value: str) -> str:
    """Case-insensitive source spelling; retain accents and punctuation."""
    return unicodedata.normalize("NFC", value).strip().casefold()


@dataclass(frozen=True)
class VarietyIdentityLink:
    source_id: str
    source_name: str
    canonical_id: str
    level: str
    evidence_ids: tuple[str, ...]
    country: str | None = None


@dataclass(frozen=True)
class VarietyIdentityDecision:
    status: str
    level: str
    canonical_id: str | None = None
    candidate_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    reason: str = ""

    @property
    def identity_confirmed(self) -> bool:
        return self.status == "RESOLVED" and self.level in {"R4", "R5"}


class VarietyIdentityRegistry:
    """Versioned, conservative resolver over explicitly reviewed evidence."""

    def __init__(self, data_path: Path | None = None) -> None:
        doc = json.loads((data_path or DATA_PATH).read_text(encoding="utf-8"))
        self.snapshot_version = doc["snapshot_version"]
        self.evidence = doc["evidence"]
        self.identities: dict[str, dict] = {}
        self.links: list[VarietyIdentityLink] = []
        for row in doc.get("identities", []):
            identity_id = row["id"]
            if not identity_id or identity_id in self.identities:
                raise ValueError(f"Duplicate or empty canonical identity: {identity_id}")
            if row.get("vivc_id") is not None:
                number = row["vivc_id"]
                if type(number) is not int or number <= 0 or identity_id != f"vivc:{number}":
                    raise ValueError("VIVC identity must retain its positive authority ID")
            self.identities[identity_id] = row
        for raw in doc.get("links", []):
            link = VarietyIdentityLink(
                source_id=raw["source_id"], source_name=raw["source_name"],
                canonical_id=raw["canonical_id"], level=raw["level"],
                evidence_ids=tuple(raw["evidence_ids"]), country=raw.get("country"),
            )
            if not link.source_id or not exact_name(link.source_name) or link.level not in LEVELS:
                raise ValueError("Invalid identity link source, name, or confidence level")
            if link.canonical_id not in self.identities:
                raise ValueError(f"Unknown canonical identity: {link.canonical_id}")
            if not link.evidence_ids or any(e not in self.evidence for e in link.evidence_ids):
                raise ValueError("Identity link requires registered evidence")
            if link.level in {"R4", "R5"}:
                qualifying = []
                for evidence_id in link.evidence_ids:
                    e = self.evidence[evidence_id]
                    if (e.get("review_status") == "reviewed"
                            and e.get("authority_type") in {"botanical_registry", "national_catalogue"}
                            and e.get("canonical_id") == link.canonical_id
                            and e.get("source_id") == link.source_id
                            and exact_name(str(e.get("source_name", ""))) == exact_name(link.source_name)
                            and e.get("country") == link.country
                            and e.get("url") and e.get("retrieved_on")
                            and e.get("relation") == ("exact_identity" if link.level == "R5" else "confirmed_synonym")):
                        qualifying.append(evidence_id)
                if not qualifying:
                    raise ValueError("R4/R5 requires a reviewed assertion for this exact source link")
            self.links.append(link)

    def resolve(self, source_name: str, *, source_id: str, country: str | None = None) -> VarietyIdentityDecision:
        name = exact_name(source_name)
        # A country-specific assertion cannot be silently widened to global scope.
        scoped = [l for l in self.links if l.source_id == source_id and
                  (l.country is None or (country is not None and exact_name(l.country) == exact_name(country)))]
        exact = [l for l in scoped if exact_name(l.source_name) == name]
        candidates = exact or [l for l in scoped if normalize_name(l.source_name) == normalize_name(source_name)]
        ids = tuple(sorted({l.canonical_id for l in candidates}))
        evidence = tuple(sorted({e for l in candidates for e in l.evidence_ids}))
        if not candidates:
            return VarietyIdentityDecision("UNKNOWN", "R1", reason="No source-specific identity evidence")
        if len(ids) > 1 or any(l.level == "R0" for l in candidates):
            return VarietyIdentityDecision("CONFLICT", "R0", candidate_ids=ids, evidence_ids=evidence,
                                           reason="Competing identities require review")
        if not exact:
            return VarietyIdentityDecision("CANDIDATE", "R2", candidate_ids=ids, evidence_ids=evidence,
                                           reason="Normalized search is not identity evidence")
        # All evidence must be reconciled before a strong link can be emitted.
        level = max((l.level for l in exact), key=lambda v: int(v[1:]))
        if level in {"R4", "R5"}:
            return VarietyIdentityDecision("RESOLVED", level, ids[0], ids, evidence,
                                           "Botanical identity only; origin permission requires legal rules")
        return VarietyIdentityDecision("CANDIDATE", level, candidate_ids=ids, evidence_ids=evidence,
                                       reason="Primary source verification incomplete")
