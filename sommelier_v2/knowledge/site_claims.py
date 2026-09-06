"""Fail-closed legal claim evaluation for named vineyard/site labels.

Named-site identity and protected-origin eligibility are separate evidence axes.
This registry only permits a site name when an explicit claim rule matches the
site and the parent wine has already passed the strict legal specification layer.
A physical site and the name legally claimed on the label are normally identical,
but some specifications explicitly allow a principal or cover name for wine from
other sites in a defined group. Those substitutions are permitted only through an
explicit ``cover_name_groups`` rule and never through generic alias inference.
Some rules also depend on lot-specific documentary facts (for example cadastral
status plus a harvest declaration); those facts must be supplied explicitly and
are never inferred from site identity.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .catalog import normalize_name
from .expanded_catalog import NamedSite
from .regional_rules import OriginDecision

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_PATH = DATA_DIR / "site_claim_rules_seed.json"


def _default_data_paths() -> list[Path]:
    """Load every reviewed site-claim tranche in deterministic filename order."""
    return sorted(DATA_DIR.glob("site_claim_rules_*.json"), key=lambda path: path.name)


@dataclass(frozen=True)
class SiteClaimRule:
    id: str
    country: str
    parent_appellation: str
    site_type: str
    required_site_legal_status: str
    required_site_source_ids: tuple[str, ...]
    allowed_wine_variants: tuple[str, ...]
    source_ids: tuple[str, ...]
    claim_kind: str
    required_claim_evidence: tuple[str, ...] = ()
    allowed_site_names: tuple[str, ...] = ()
    excluded_site_names: tuple[str, ...] = ()
    cover_name_groups: tuple[tuple[str, tuple[str, ...]], ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class SiteClaimDecision:
    eligible: bool
    status: str
    site_id: str | None
    rule_id: str | None = None
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    claim_name: str | None = None


class SiteClaimRegistry:
    """Evaluate whether a known physical site can support a requested label claim."""

    def __init__(self, data_path: Path | None = None) -> None:
        paths = [Path(data_path)] if data_path is not None else _default_data_paths()
        documents: list[dict] = []
        for path in paths:
            if not path.exists():
                if data_path is not None:
                    raise FileNotFoundError(path)
                continue
            doc = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise ValueError(f"{path.name} must contain a JSON object")
            documents.append(doc)

        self.sources: dict[str, dict] = {}
        raw_rules: list[dict] = []
        for doc in documents:
            for source_id, source in dict(doc.get("sources", {})).items():
                source_row = dict(source)
                existing = self.sources.get(str(source_id))
                if existing is not None and existing != source_row:
                    raise ValueError(f"Conflicting site-claim source definition: {source_id}")
                self.sources[str(source_id)] = source_row
            for row in doc.get("rules", []):
                if isinstance(row, dict):
                    raw_rules.append(row)

        self.rules: list[SiteClaimRule] = []
        seen: set[str] = set()
        for row in raw_rules:
            rule_id = str(row.get("id") or "").strip()
            if not rule_id:
                raise ValueError("Site-claim rule is missing an id")
            if rule_id in seen:
                raise ValueError(f"Duplicate site-claim rule id: {rule_id}")
            seen.add(rule_id)

            source_ids = tuple(str(v) for v in row.get("source_ids", []))
            missing = [source_id for source_id in source_ids if source_id not in self.sources]
            if missing:
                raise ValueError(f"{rule_id} references unknown claim sources: {missing}")

            required_claim_evidence = tuple(
                str(value).strip()
                for value in row.get("required_claim_evidence", [])
                if str(value).strip()
            )
            if len(set(required_claim_evidence)) != len(required_claim_evidence):
                raise ValueError(f"{rule_id} contains duplicate required claim evidence tokens")

            allowed_site_names = tuple(str(v) for v in row.get("allowed_site_names", []))
            excluded_site_names = tuple(str(v) for v in row.get("excluded_site_names", []))
            overlap = {
                normalize_name(name) for name in allowed_site_names
            } & {
                normalize_name(name) for name in excluded_site_names
            }
            if overlap:
                raise ValueError(
                    f"{rule_id} lists the same site in allowed_site_names and excluded_site_names"
                )

            raw_cover_groups = row.get("cover_name_groups", {})
            if raw_cover_groups in (None, ""):
                raw_cover_groups = {}
            if not isinstance(raw_cover_groups, dict):
                raise ValueError(f"{rule_id} cover_name_groups must be a JSON object")
            cover_name_groups: list[tuple[str, tuple[str, ...]]] = []
            seen_cover_names: set[str] = set()
            for raw_claim_name, raw_physical_names in raw_cover_groups.items():
                claim_name = str(raw_claim_name).strip()
                if not claim_name:
                    raise ValueError(f"{rule_id} contains an empty cover claim name")
                normalized_claim = normalize_name(claim_name)
                if normalized_claim in seen_cover_names:
                    raise ValueError(f"{rule_id} contains a duplicate cover claim name: {claim_name}")
                seen_cover_names.add(normalized_claim)
                if not isinstance(raw_physical_names, list) or not raw_physical_names:
                    raise ValueError(
                        f"{rule_id} cover claim {claim_name!r} must list at least one physical site"
                    )
                physical_names = tuple(
                    str(value).strip() for value in raw_physical_names if str(value).strip()
                )
                if not physical_names:
                    raise ValueError(
                        f"{rule_id} cover claim {claim_name!r} has no usable physical site names"
                    )
                cover_name_groups.append((claim_name, physical_names))

            self.rules.append(
                SiteClaimRule(
                    id=rule_id,
                    country=str(row.get("country") or ""),
                    parent_appellation=str(row.get("parent_appellation") or ""),
                    site_type=str(row.get("site_type") or ""),
                    required_site_legal_status=str(row.get("required_site_legal_status") or ""),
                    required_site_source_ids=tuple(str(v) for v in row.get("required_site_source_ids", [])),
                    allowed_wine_variants=tuple(str(v) for v in row.get("allowed_wine_variants", [])),
                    source_ids=source_ids,
                    claim_kind=str(row.get("claim_kind") or "named_site"),
                    required_claim_evidence=required_claim_evidence,
                    allowed_site_names=allowed_site_names,
                    excluded_site_names=excluded_site_names,
                    cover_name_groups=tuple(cover_name_groups),
                    notes=str(row.get("notes") or ""),
                )
            )

    @staticmethod
    def _same(left: str | None, right: str | None) -> bool:
        return normalize_name(left or "") == normalize_name(right or "")

    @staticmethod
    def _variant_matches(rule: SiteClaimRule, wine_variant: str | None) -> bool:
        if not rule.allowed_wine_variants:
            return True
        requested = normalize_name(wine_variant or "")
        return any(requested == normalize_name(allowed) for allowed in rule.allowed_wine_variants)

    @staticmethod
    def _site_name_matches(rule: SiteClaimRule, site_name: str) -> bool:
        normalized = normalize_name(site_name)
        if rule.allowed_site_names and normalized not in {
            normalize_name(name) for name in rule.allowed_site_names
        }:
            return False
        if normalized in {normalize_name(name) for name in rule.excluded_site_names}:
            return False
        return True

    @classmethod
    def _claim_name_matches(
        cls,
        rule: SiteClaimRule,
        *,
        physical_site_name: str,
        claimed_site_name: str,
    ) -> bool:
        """Return True only for an exact claim or an explicitly mapped cover claim."""
        if cls._same(physical_site_name, claimed_site_name):
            return True
        for cover_name, physical_names in rule.cover_name_groups:
            if not cls._same(cover_name, claimed_site_name):
                continue
            return any(cls._same(physical_site_name, name) for name in physical_names)
        return False

    def _source_evidence(self, rule: SiteClaimRule) -> tuple[str, ...]:
        evidence: list[str] = []
        for source_id in rule.source_ids:
            source = self.sources.get(source_id, {})
            url = str(source.get("url") or "").strip()
            evidence.append(f"site_claim_rule:{rule.id}:{source_id}")
            if url:
                evidence.append(f"source_url:{url}")
        return tuple(evidence)

    def evaluate(
        self,
        *,
        site: NamedSite | None,
        origin_decision: OriginDecision,
        appellation: str | None,
        wine_variant: str | None = None,
        claimed_site_name: str | None = None,
        claim_evidence: Sequence[str] = (),
    ) -> SiteClaimDecision:
        if site is None:
            return SiteClaimDecision(False, "site_claim_not_requested", None)

        requested_claim = site.name if claimed_site_name is None else str(claimed_site_name).strip()
        if not requested_claim:
            return SiteClaimDecision(
                False,
                "site_claim_name_empty",
                site.id,
                issues=("A requested site claim name cannot be empty.",),
            )
        if origin_decision.label_scope.casefold() != "regulated_gi":
            return SiteClaimDecision(
                False,
                "site_claim_requires_regulated_gi",
                site.id,
                issues=("A named-site legal label claim requires a regulated GI context.",),
                claim_name=requested_claim,
            )
        if not origin_decision.eligible:
            return SiteClaimDecision(
                False,
                "parent_origin_not_eligible",
                site.id,
                issues=("The parent protected-origin claim is not eligible.",),
                claim_name=requested_claim,
            )
        if origin_decision.status != "appellation_eligible_sourced_spec":
            return SiteClaimDecision(
                False,
                "strict_parent_spec_required_for_site_claim",
                site.id,
                issues=("The parent origin has not passed a reviewed strict legal specification.",),
                claim_name=requested_claim,
            )

        parent = appellation or site.parent
        candidates = [
            rule
            for rule in self.rules
            if self._same(rule.country, site.country)
            and self._same(rule.parent_appellation, parent)
            and self._same(rule.site_type, site.site_type)
        ]
        if not candidates:
            return SiteClaimDecision(
                False,
                "site_claim_rule_unverified",
                site.id,
                issues=(
                    "The site is documented, but no positive legal label-claim rule is verified for this site type and parent appellation.",
                ),
                claim_name=requested_claim,
            )

        site_sources = {str(source_id) for source_id in site.source_ids}
        provided_claim_evidence = {
            str(value).strip() for value in claim_evidence if str(value).strip()
        }
        mismatch_reasons: list[str] = []
        for rule in candidates:
            if rule.required_site_legal_status and not self._same(rule.required_site_legal_status, site.legal_status):
                mismatch_reasons.append(
                    f"{rule.id}: site legal status {site.legal_status!r} does not match the verified rule."
                )
                continue
            if rule.required_site_source_ids and not set(rule.required_site_source_ids).issubset(site_sources):
                mismatch_reasons.append(f"{rule.id}: required site-identity evidence is missing.")
                continue
            missing_claim_evidence = [
                token for token in rule.required_claim_evidence
                if token not in provided_claim_evidence
            ]
            if missing_claim_evidence:
                mismatch_reasons.append(
                    f"{rule.id}: required lot-specific claim evidence is missing: {', '.join(missing_claim_evidence)}."
                )
                continue
            if not self._variant_matches(rule, wine_variant):
                allowed = ", ".join(rule.allowed_wine_variants)
                mismatch_reasons.append(
                    f"{rule.id}: this claim is restricted to wine variant(s): {allowed}."
                )
                continue
            if not self._site_name_matches(rule, site.name):
                mismatch_reasons.append(
                    f"{rule.id}: site {site.name!r} is outside the verified site-name set for this rule."
                )
                continue
            if not self._claim_name_matches(
                rule,
                physical_site_name=site.name,
                claimed_site_name=requested_claim,
            ):
                mismatch_reasons.append(
                    f"{rule.id}: physical site {site.name!r} cannot use requested claim {requested_claim!r}."
                )
                continue

            evidence = list(self._source_evidence(rule))
            evidence.extend(
                f"claim_evidence:{token}" for token in rule.required_claim_evidence
            )
            if not self._same(site.name, requested_claim):
                evidence.append(f"physical_site:{site.name}")
                evidence.append(f"authorized_cover_claim:{requested_claim}")
            return SiteClaimDecision(
                True,
                "site_claim_eligible_verified_rule",
                site.id,
                rule_id=rule.id,
                warnings=(rule.notes,) if rule.notes else (),
                evidence=tuple(evidence),
                claim_name=requested_claim,
            )

        return SiteClaimDecision(
            False,
            "site_claim_rule_conditions_not_met",
            site.id,
            issues=tuple(mismatch_reasons) or ("A site-claim rule exists, but its conditions are not met.",),
            claim_name=requested_claim,
        )

    def stats(self) -> dict[str, int]:
        parents = {
            (normalize_name(rule.country), normalize_name(rule.parent_appellation))
            for rule in self.rules
        }
        return {
            "verified_site_claim_rules": len(self.rules),
            "verified_site_claim_parent_appellations": len(parents),
            "verified_site_claim_sources": len(self.sources),
            "verified_site_claim_rules_with_evidence_requirements": sum(
                bool(rule.required_claim_evidence) for rule in self.rules
            ),
            "verified_site_cover_name_groups": sum(
                len(rule.cover_name_groups) for rule in self.rules
            ),
        }
