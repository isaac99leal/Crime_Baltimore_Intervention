"""Evidence-reviewed botanical identity links; never an appellation permit.

Names folded for search only produce R2 candidates. An R4/R5 link requires a
reviewed, source-specific assertion, not merely a matching catalogue title.
The source assertion remains distinct from the legacy GrapeKnowledge profile.

The default registry loads one canonical base document plus sorted additive
shards. Passing ``data_path`` keeps the historical single-document behavior so
unit tests and callers can validate an isolated evidence document.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import unicodedata

from .catalog import normalize_name

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_PATH = DATA_DIR / "variety_identity_evidence.json"
DATA_SHARD_GLOB = "variety_identity_evidence_shard_*.json"
CONFLICT_DATA_PATH = DATA_DIR / "variety_identity_conflicts.json"
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
class VarietyIdentityConflict:
    id: str
    source_id: str
    source_name: str
    candidate_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    conflict_class: str
    status: str
    generator_policy: str
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
        paths = [data_path] if data_path is not None else [
            DATA_PATH,
            *sorted(DATA_DIR.glob(DATA_SHARD_GLOB)),
        ]
        docs = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        if not docs:
            raise ValueError("Variety identity registry requires at least one evidence document")

        self.snapshot_versions = tuple(doc["snapshot_version"] for doc in docs)
        self.snapshot_version = self.snapshot_versions[-1]
        self.evidence: dict[str, dict] = {}
        self.identities: dict[str, dict] = {}
        self.links: list[VarietyIdentityLink] = []
        self.conflict_evidence: dict[str, dict] = {}
        self.conflicts: list[VarietyIdentityConflict] = []

        if data_path is None and CONFLICT_DATA_PATH.exists():
            conflict_doc = json.loads(CONFLICT_DATA_PATH.read_text(encoding="utf-8"))
            for evidence_id, row in conflict_doc.get("evidence", {}).items():
                if not evidence_id or evidence_id in self.conflict_evidence:
                    raise ValueError(f"Duplicate or empty conflict evidence identifier: {evidence_id}")
                self.conflict_evidence[evidence_id] = row

            seen_conflict_ids: set[str] = set()
            seen_conflict_keys: set[tuple[str, str, str | None]] = set()
            for raw in conflict_doc.get("conflicts", []):
                conflict_id = str(raw.get("id") or "").strip()
                source_id = str(raw.get("source_id") or "").strip()
                source_name = str(raw.get("source_name") or "").strip()
                country = raw.get("country")
                candidate_ids = tuple(str(v) for v in raw.get("candidate_ids", []))
                evidence_ids = tuple(str(v) for v in raw.get("evidence_ids", []))
                if not conflict_id or conflict_id in seen_conflict_ids:
                    raise ValueError(f"Duplicate or empty variety identity conflict id: {conflict_id}")
                seen_conflict_ids.add(conflict_id)
                if not source_id or not exact_name(source_name):
                    raise ValueError(f"{conflict_id} requires source_id and source_name")
                if not candidate_ids or any(
                    not value.startswith("vivc:") or not value[5:].isdigit()
                    for value in candidate_ids
                ):
                    raise ValueError(f"{conflict_id} requires one or more VIVC candidate ids")
                if not evidence_ids or any(
                    value not in self.conflict_evidence for value in evidence_ids
                ):
                    raise ValueError(f"{conflict_id} requires registered conflict evidence")
                if raw.get("generator_policy") != "block_identity_promotion":
                    raise ValueError(f"{conflict_id} must block identity promotion")
                key = (
                    source_id,
                    exact_name(source_name),
                    exact_name(country) if country is not None else None,
                )
                if key in seen_conflict_keys:
                    raise ValueError(f"Duplicate variety identity conflict key: {key}")
                seen_conflict_keys.add(key)
                self.conflicts.append(
                    VarietyIdentityConflict(
                        id=conflict_id,
                        source_id=source_id,
                        source_name=source_name,
                        candidate_ids=candidate_ids,
                        evidence_ids=evidence_ids,
                        conflict_class=str(raw.get("conflict_class") or "unspecified"),
                        status=str(raw.get("status") or "open"),
                        generator_policy="block_identity_promotion",
                        country=country,
                    )
                )

        # Evidence identifiers are immutable provenance keys. Duplicate keys
        # across shards are rejected even if their payloads happen to match.
        for doc in docs:
            for evidence_id, row in doc.get("evidence", {}).items():
                if not evidence_id or evidence_id in self.evidence:
                    raise ValueError(f"Duplicate or empty evidence identifier: {evidence_id}")
                self.evidence[evidence_id] = row

        # Canonical identities are authority identifiers, not source-row names.
        # A later shard can link to an earlier identity without redefining it.
        for doc in docs:
            for row in doc.get("identities", []):
                identity_id = row["id"]
                if not identity_id or identity_id in self.identities:
                    raise ValueError(f"Duplicate or empty canonical identity: {identity_id}")
                if row.get("vivc_id") is not None:
                    number = row["vivc_id"]
                    if type(number) is not int or number <= 0 or identity_id != f"vivc:{number}":
                        raise ValueError("VIVC identity must retain its positive authority ID")
                self.identities[identity_id] = row

        link_keys: set[tuple[str, str, str | None, str, str]] = set()
        for doc in docs:
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
                key = (
                    link.source_id,
                    exact_name(link.source_name),
                    exact_name(link.country) if link.country is not None else None,
                    link.canonical_id,
                    link.level,
                )
                if key in link_keys:
                    raise ValueError("Duplicate variety identity link across evidence documents")
                link_keys.add(key)
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
        matching_conflicts = [
            conflict
            for conflict in self.conflicts
            if conflict.source_id == source_id
            and exact_name(conflict.source_name) == name
            and (
                conflict.country is None
                or (country is not None and exact_name(conflict.country) == exact_name(country))
            )
            and conflict.status == "open"
        ]
        if matching_conflicts:
            candidate_ids = tuple(
                sorted({candidate for conflict in matching_conflicts for candidate in conflict.candidate_ids})
            )
            evidence_ids = tuple(
                sorted({evidence for conflict in matching_conflicts for evidence in conflict.evidence_ids})
            )
            classes = ", ".join(sorted({conflict.conflict_class for conflict in matching_conflicts}))
            return VarietyIdentityDecision(
                "CONFLICT",
                "R0",
                candidate_ids=candidate_ids,
                evidence_ids=evidence_ids,
                reason=f"Source-backed identity conflict requires review: {classes}",
            )

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
