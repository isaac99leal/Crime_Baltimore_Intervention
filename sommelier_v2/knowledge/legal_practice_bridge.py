"""Bridge reviewed legal-spec fields to winemaking decision authority.

This module is intentionally narrow. A legal specification can only promote a
winemaking decision when the structured legal field directly answers that
question. Absence of a restriction is never interpreted as permission.

Examples:
* ``manual_harvest_required=True`` confirms hand harvest and rejects machine
  harvest. ``False`` does not prove machine harvest is allowed.
* an explicitly recognized sparkling production method can confirm or reject
  the corresponding secondary-fermentation option. An unknown method string
  leaves the decision unresolved.

All other cellar choices remain unresolved until the legal-spec schema contains
an explicit reviewed field for that practice.
"""
from __future__ import annotations

from dataclasses import dataclass

from .catalog import normalize_name
from .legal_specs import LegalWineSpec
from .winemaking_decisions import (
    DecisionAuthorityAssessment,
    WinemakingDecisionError,
    WinemakingDecisionRegistry,
)


@dataclass(frozen=True)
class LegalPracticeAssessment:
    spec_id: str
    decision_id: str
    option_id: str
    legal_confirmation: bool | None
    status: str
    reason: str
    evidence_source_ids: tuple[str, ...]


_SPARKLING_METHOD_ALIASES: dict[str, frozenset[str]] = {
    "traditional": frozenset(
        {
            "traditional",
            "traditional method",
            "traditional bottle method",
            "bottle fermentation",
            "bottle fermented",
            "methode traditionnelle",
            "méthode traditionnelle",
            "metodo classico",
            "método tradicional",
        }
    ),
    "tank": frozenset(
        {
            "tank",
            "tank method",
            "charmat",
            "charmat method",
            "martinotti",
            "martinotti method",
        }
    ),
    "ancestral": frozenset(
        {
            "ancestral",
            "ancestral method",
            "methode ancestrale",
            "méthode ancestrale",
        }
    ),
}


def _canonical_sparkling_method(value: str | None) -> str | None:
    if not value:
        return None
    key = normalize_name(value)
    for option_id, aliases in _SPARKLING_METHOD_ALIASES.items():
        if key in {normalize_name(alias) for alias in aliases}:
            return option_id
    return None


class LegalPracticeBridge:
    """Promote only legal conclusions directly supported by structured specs."""

    def __init__(self, decisions: WinemakingDecisionRegistry | None = None) -> None:
        self.decisions = decisions or WinemakingDecisionRegistry()

    def assess_option(
        self,
        spec: LegalWineSpec,
        decision_id: str,
        option_id: str,
    ) -> LegalPracticeAssessment:
        decision = self.decisions.decision(decision_id)
        if decision is None:
            raise WinemakingDecisionError(f"Unknown winemaking decision {decision_id!r}")
        option = decision.option(option_id)
        if option is None:
            raise WinemakingDecisionError(
                f"Unknown option {option_id!r} for decision {decision_id!r}"
            )

        evidence = tuple(spec.source_ids)

        if not decision.requires_designation_check:
            return LegalPracticeAssessment(
                spec_id=spec.id,
                decision_id=decision.id,
                option_id=option.id,
                legal_confirmation=None,
                status="no_designation_gate_in_decision_matrix",
                reason=(
                    "This simulator decision does not require a designation gate. "
                    "The legal specification is therefore not used to manufacture a permission claim."
                ),
                evidence_source_ids=evidence,
            )

        if decision.id == "harvest-method":
            return self._assess_harvest_method(spec, option.id, evidence)

        if decision.id == "sparkling-secondary":
            return self._assess_sparkling_method(spec, option.id, evidence)

        return LegalPracticeAssessment(
            spec_id=spec.id,
            decision_id=decision.id,
            option_id=option.id,
            legal_confirmation=None,
            status="legal_practice_rule_not_structured",
            reason=(
                "The reviewed legal specification does not expose a structured field that directly "
                "answers this cellar-practice choice. The decision remains unresolved."
            ),
            evidence_source_ids=evidence,
        )

    @staticmethod
    def _assess_harvest_method(
        spec: LegalWineSpec,
        option_id: str,
        evidence: tuple[str, ...],
    ) -> LegalPracticeAssessment:
        if not spec.manual_harvest_required:
            return LegalPracticeAssessment(
                spec_id=spec.id,
                decision_id="harvest-method",
                option_id=option_id,
                legal_confirmation=None,
                status="manual_harvest_not_explicitly_required",
                reason=(
                    "The structured specification does not require manual harvest. "
                    "That absence does not prove that machine harvest is permitted."
                ),
                evidence_source_ids=evidence,
            )

        if option_id == "hand":
            return LegalPracticeAssessment(
                spec_id=spec.id,
                decision_id="harvest-method",
                option_id=option_id,
                legal_confirmation=True,
                status="confirmed_by_explicit_manual_harvest_requirement",
                reason="The reviewed specification explicitly requires manual harvest.",
                evidence_source_ids=evidence,
            )
        if option_id == "machine":
            return LegalPracticeAssessment(
                spec_id=spec.id,
                decision_id="harvest-method",
                option_id=option_id,
                legal_confirmation=False,
                status="prohibited_by_explicit_manual_harvest_requirement",
                reason="Machine harvest conflicts with the explicit manual-harvest requirement.",
                evidence_source_ids=evidence,
            )

        return LegalPracticeAssessment(
            spec_id=spec.id,
            decision_id="harvest-method",
            option_id=option_id,
            legal_confirmation=None,
            status="unmapped_harvest_method",
            reason="The harvest-method option is not mapped to the structured legal field.",
            evidence_source_ids=evidence,
        )

    @staticmethod
    def _assess_sparkling_method(
        spec: LegalWineSpec,
        option_id: str,
        evidence: tuple[str, ...],
    ) -> LegalPracticeAssessment:
        required = _canonical_sparkling_method(spec.required_method)
        if required is None:
            return LegalPracticeAssessment(
                spec_id=spec.id,
                decision_id="sparkling-secondary",
                option_id=option_id,
                legal_confirmation=None,
                status="sparkling_method_not_structured_or_unrecognized",
                reason=(
                    "No recognized structured sparkling method can be derived from required_method; "
                    "the bridge does not infer one from appellation identity or wine style."
                ),
                evidence_source_ids=evidence,
            )

        # 'none' is incompatible with any explicit sparkling secondary method.
        if option_id == "none":
            return LegalPracticeAssessment(
                spec_id=spec.id,
                decision_id="sparkling-secondary",
                option_id=option_id,
                legal_confirmation=False,
                status="prohibited_by_explicit_sparkling_method",
                reason=f"The specification explicitly requires the {required} sparkling method.",
                evidence_source_ids=evidence,
            )
        if option_id == required:
            return LegalPracticeAssessment(
                spec_id=spec.id,
                decision_id="sparkling-secondary",
                option_id=option_id,
                legal_confirmation=True,
                status="confirmed_by_explicit_sparkling_method",
                reason=f"The selected method matches the explicit {required} method requirement.",
                evidence_source_ids=evidence,
            )
        if option_id in _SPARKLING_METHOD_ALIASES:
            return LegalPracticeAssessment(
                spec_id=spec.id,
                decision_id="sparkling-secondary",
                option_id=option_id,
                legal_confirmation=False,
                status="prohibited_by_conflicting_sparkling_method",
                reason=(
                    f"The selected {option_id} method conflicts with the explicit {required} method requirement."
                ),
                evidence_source_ids=evidence,
            )

        return LegalPracticeAssessment(
            spec_id=spec.id,
            decision_id="sparkling-secondary",
            option_id=option_id,
            legal_confirmation=None,
            status="unmapped_sparkling_method",
            reason="The selected sparkling option is not mapped to the structured method vocabulary.",
            evidence_source_ids=evidence,
        )

    def authority_assessment(
        self,
        spec: LegalWineSpec,
        decision_id: str,
        option_id: str,
    ) -> DecisionAuthorityAssessment:
        """Return the decision registry's authority state using only bridge evidence."""
        practice = self.assess_option(spec, decision_id, option_id)
        return self.decisions.assess_authority(
            decision_id,
            legal_confirmation=practice.legal_confirmation,
        )
