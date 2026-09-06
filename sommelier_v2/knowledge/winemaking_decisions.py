"""Winemaking decision matrix with explicit legal-authority boundaries.

The recovered decision matrix contains useful process choices and bounded sensory
or risk transforms for the simulator. Those transforms are *derived simulation
priors*. Source references support the existence, mechanism, or product context
of a practice; they do not make the matrix a legal rulebook.

Most importantly, OIV recognition does not establish that a practice is allowed
for a particular GI, PDO, DOC, AVA, or other protected product. Decisions marked
``requiresDesignationCheck`` fail closed until an external legal/product-spec
layer supplies an explicit confirmation.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .catalog import normalize_name
from .process_chemistry_evidence import ProcessChemistryEvidenceRegistry

DATA_DIR = Path(__file__).resolve().parent / "data" / "winemaking_decisions"


class WinemakingDecisionError(ValueError):
    """Raised when decision data or authority handling violates invariants."""


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _ordered_files(prefix: str) -> list[Path]:
    def key(path: Path) -> tuple[int, str]:
        stem = path.stem
        if "_pass" not in stem:
            return (0, stem)
        try:
            return (int(stem.rsplit("_pass", 1)[1]), stem)
        except ValueError:
            return (9999, stem)

    return sorted(DATA_DIR.glob(f"{prefix}*.json"), key=key)


@dataclass(frozen=True)
class DecisionEvidenceSource:
    id: str
    publisher: str
    title: str
    url: str
    jurisdiction: str
    kind: str
    accessed: str
    source_family: str


@dataclass(frozen=True)
class DecisionOption:
    id: str
    label: str
    matrix: Mapping[str, float]

    def effect(self, axis: str) -> float:
        return float(self.matrix.get(axis, 0.0))


@dataclass(frozen=True)
class WinemakingDecision:
    id: str
    stage: str
    name: str
    requires_designation_check: bool
    source_refs: tuple[str, ...]
    options: tuple[DecisionOption, ...]
    authority_scopes: tuple[str, ...]

    def option(self, option_id: str) -> DecisionOption | None:
        key = normalize_name(option_id)
        return next((option for option in self.options if normalize_name(option.id) == key), None)


@dataclass(frozen=True)
class DecisionAuthorityAssessment:
    decision_id: str
    requires_designation_check: bool
    legal_confirmation: bool | None
    allowed: bool | None
    status: str
    source_authority_is_sufficient: bool
    authority_scopes: tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class WinemakingDecisionStats:
    decision_count: int
    option_count: int
    stage_count: int
    axis_count: int
    decisions_requiring_designation_check: int
    sourced_decision_count: int
    referenced_source_count: int


class WinemakingDecisionRegistry:
    """Immutable process-decision registry with fail-closed legal promotion."""

    def __init__(
        self,
        data_dir: Path = DATA_DIR,
        *,
        chemistry_evidence: ProcessChemistryEvidenceRegistry | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.axes: tuple[str, ...] = ()
        self.matrix_scale: str = ""
        self.decisions: tuple[WinemakingDecision, ...] = ()
        self.sources: tuple[DecisionEvidenceSource, ...] = ()
        self._decision_index: dict[str, WinemakingDecision] = {}
        self._source_index: dict[str, DecisionEvidenceSource] = {}
        self._load_sources(chemistry_evidence or ProcessChemistryEvidenceRegistry())
        self._load_decisions()

    def _load_sources(self, chemistry: ProcessChemistryEvidenceRegistry) -> None:
        sources: dict[str, DecisionEvidenceSource] = {}
        for path in _ordered_files("sources_pass"):
            doc = json.loads(path.read_text(encoding="utf-8"))
            for raw in doc.get("sources", []):
                source_id = str(raw.get("id", "")).strip()
                if not source_id:
                    raise WinemakingDecisionError(f"Missing source id in {path.name}")
                if source_id in sources:
                    raise WinemakingDecisionError(f"Duplicate decision-source id {source_id}")
                url = str(raw.get("url", "")).strip()
                if not url.startswith(("https://", "http://")):
                    raise WinemakingDecisionError(f"Decision source {source_id} lacks an absolute URL")
                source = DecisionEvidenceSource(
                    id=source_id,
                    publisher=str(raw.get("publisher", "")).strip(),
                    title=str(raw.get("title", "")).strip(),
                    url=url,
                    jurisdiction=str(raw.get("jurisdiction", "")).strip(),
                    kind=str(raw.get("kind", "")).strip(),
                    accessed=str(raw.get("accessed", "")).strip(),
                    source_family="winemaking_decision_source",
                )
                if not source.publisher or not source.title or not source.jurisdiction or not source.kind:
                    raise WinemakingDecisionError(f"Incomplete decision source metadata for {source_id}")
                sources[source_id] = source

        # Reuse the canonical chemistry source graph instead of duplicating AWRI
        # source registries inside the decision corpus.
        for source in chemistry.sources:
            candidate = DecisionEvidenceSource(
                id=source.id,
                publisher=source.publisher,
                title=source.title,
                url=source.url,
                jurisdiction=source.jurisdiction,
                kind=source.kind,
                accessed=source.accessed,
                source_family="process_chemistry_evidence",
            )
            existing = sources.get(source.id)
            if existing is not None and existing != candidate:
                raise WinemakingDecisionError(
                    f"Conflicting metadata for shared source {source.id}"
                )
            sources[source.id] = candidate

        self._source_index = sources

    def _load_decisions(self) -> None:
        decisions: list[WinemakingDecision] = []
        seen_decisions: set[str] = set()
        expected_axes: tuple[str, ...] | None = None
        expected_scale: str | None = None
        referenced_sources: set[str] = set()

        files = _ordered_files("winemaking_decisions")
        if not files:
            raise WinemakingDecisionError(f"No winemaking decision files found in {self.data_dir}")

        for path in files:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("schemaVersion") != 1:
                raise WinemakingDecisionError(f"Unsupported decision schema in {path.name}")
            axes_raw = doc.get("axes", [])
            if not isinstance(axes_raw, list) or not axes_raw:
                raise WinemakingDecisionError(f"Decision file {path.name} has no axes")
            axes = tuple(str(axis).strip() for axis in axes_raw)
            if len(set(axes)) != len(axes):
                raise WinemakingDecisionError(f"Decision file {path.name} has duplicate axes")
            if expected_axes is None:
                expected_axes = axes
            elif axes != expected_axes:
                raise WinemakingDecisionError(
                    f"Decision axes changed between passes: {expected_axes!r} vs {axes!r}"
                )

            scale = str(doc.get("matrixScale", "")).strip()
            if not scale:
                raise WinemakingDecisionError(f"Decision file {path.name} lacks matrixScale")
            if expected_scale is None:
                expected_scale = scale
            elif scale != expected_scale:
                raise WinemakingDecisionError("Decision matrix scale changed between passes")

            for raw in doc.get("decisions", []):
                decision_id = str(raw.get("id", "")).strip()
                if not decision_id or decision_id in seen_decisions:
                    raise WinemakingDecisionError(
                        f"Missing or duplicate decision id {decision_id!r}"
                    )
                stage = str(raw.get("stage", "")).strip()
                name = str(raw.get("name", "")).strip()
                designation_check = raw.get("requiresDesignationCheck")
                if not stage or not name or not isinstance(designation_check, bool):
                    raise WinemakingDecisionError(f"Incomplete decision metadata for {decision_id}")

                source_refs = tuple(
                    str(source_ref).strip()
                    for source_ref in raw.get("sourceRefs", [])
                    if str(source_ref).strip()
                )
                for source_ref in source_refs:
                    if source_ref not in self._source_index:
                        raise WinemakingDecisionError(
                            f"Decision {decision_id} references unknown source {source_ref}"
                        )
                    referenced_sources.add(source_ref)

                options_raw = raw.get("options", [])
                if not isinstance(options_raw, list) or not options_raw:
                    raise WinemakingDecisionError(f"Decision {decision_id} has no options")
                options: list[DecisionOption] = []
                seen_options: set[str] = set()
                for raw_option in options_raw:
                    option_id = str(raw_option.get("id", "")).strip()
                    label = str(raw_option.get("label", "")).strip()
                    if not option_id or option_id in seen_options or not label:
                        raise WinemakingDecisionError(
                            f"Missing/duplicate option in decision {decision_id}: {option_id!r}"
                        )
                    matrix_raw = raw_option.get("matrix", {})
                    if not isinstance(matrix_raw, dict):
                        raise WinemakingDecisionError(
                            f"Decision {decision_id}/{option_id} matrix must be an object"
                        )
                    matrix: dict[str, float] = {}
                    for axis, raw_value in matrix_raw.items():
                        if axis not in axes:
                            raise WinemakingDecisionError(
                                f"Decision {decision_id}/{option_id} uses unknown axis {axis!r}"
                            )
                        if not isinstance(raw_value, (int, float)) or isinstance(raw_value, bool):
                            raise WinemakingDecisionError(
                                f"Decision {decision_id}/{option_id}/{axis} must be numeric"
                            )
                        value = float(raw_value)
                        if not -1.0 <= value <= 1.0:
                            raise WinemakingDecisionError(
                                f"Decision {decision_id}/{option_id}/{axis} must be within -1..1"
                            )
                        matrix[str(axis)] = value
                    options.append(
                        DecisionOption(
                            id=option_id,
                            label=label,
                            matrix=MappingProxyType(matrix),
                        )
                    )
                    seen_options.add(option_id)

                scopes = tuple(
                    dict.fromkeys(
                        self._source_index[source_ref].jurisdiction
                        for source_ref in source_refs
                    )
                )
                decision = WinemakingDecision(
                    id=decision_id,
                    stage=stage,
                    name=name,
                    requires_designation_check=designation_check,
                    source_refs=source_refs,
                    options=tuple(options),
                    authority_scopes=scopes,
                )
                decisions.append(decision)
                seen_decisions.add(decision_id)

        self.axes = expected_axes or ()
        self.matrix_scale = expected_scale or ""
        self.decisions = tuple(decisions)
        self._decision_index = {decision.id: decision for decision in decisions}
        self.sources = tuple(
            self._source_index[source_id] for source_id in sorted(referenced_sources)
        )

    def decision(self, decision_id: str) -> WinemakingDecision | None:
        return self._decision_index.get(decision_id)

    def source(self, source_id: str) -> DecisionEvidenceSource | None:
        return self._source_index.get(source_id)

    def by_stage(self, stage: str) -> tuple[WinemakingDecision, ...]:
        key = normalize_name(stage)
        return tuple(
            decision for decision in self.decisions
            if normalize_name(decision.stage) == key
        )

    def option_matrix(self, decision_id: str, option_id: str) -> Mapping[str, float]:
        decision = self.decision(decision_id)
        if decision is None:
            raise WinemakingDecisionError(f"Unknown winemaking decision {decision_id!r}")
        option = decision.option(option_id)
        if option is None:
            raise WinemakingDecisionError(
                f"Unknown option {option_id!r} for decision {decision_id!r}"
            )
        return option.matrix

    def assess_authority(
        self,
        decision_id: str,
        *,
        legal_confirmation: bool | None = None,
    ) -> DecisionAuthorityAssessment:
        """Assess whether the matrix itself is enough to authorize a practice.

        ``legal_confirmation`` represents the result of a separate legal or
        product-spec validation layer. It is never inferred from OIV or other
        mechanism evidence stored on the decision.
        """
        decision = self.decision(decision_id)
        if decision is None:
            raise WinemakingDecisionError(f"Unknown winemaking decision {decision_id!r}")

        if decision.requires_designation_check:
            if legal_confirmation is None:
                return DecisionAuthorityAssessment(
                    decision_id=decision.id,
                    requires_designation_check=True,
                    legal_confirmation=None,
                    allowed=None,
                    status="requires_external_legal_confirmation",
                    source_authority_is_sufficient=False,
                    authority_scopes=decision.authority_scopes,
                    explanation=(
                        "The decision matrix cannot authorize this practice for a protected product. "
                        "A separate legal/product-spec validation result is required."
                    ),
                )
            if legal_confirmation is False:
                return DecisionAuthorityAssessment(
                    decision_id=decision.id,
                    requires_designation_check=True,
                    legal_confirmation=False,
                    allowed=False,
                    status="prohibited_by_external_legal_layer",
                    source_authority_is_sufficient=False,
                    authority_scopes=decision.authority_scopes,
                    explanation=(
                        "The external legal/product-spec layer rejected the practice for the requested product."
                    ),
                )
            return DecisionAuthorityAssessment(
                decision_id=decision.id,
                requires_designation_check=True,
                legal_confirmation=True,
                allowed=True,
                status="confirmed_by_external_legal_layer",
                source_authority_is_sufficient=False,
                authority_scopes=decision.authority_scopes,
                explanation=(
                    "The practice is allowed only because a separate legal/product-spec layer confirmed it; "
                    "the decision matrix did not supply that authority."
                ),
            )

        return DecisionAuthorityAssessment(
            decision_id=decision.id,
            requires_designation_check=False,
            legal_confirmation=legal_confirmation,
            allowed=True,
            status="process_available_no_matrix_designation_gate",
            source_authority_is_sufficient=False,
            authority_scopes=decision.authority_scopes,
            explanation=(
                "The matrix does not require a designation-specific gate for this simulator choice. "
                "This is not a claim that the matrix establishes GI law."
            ),
        )

    def stats(self) -> WinemakingDecisionStats:
        return WinemakingDecisionStats(
            decision_count=len(self.decisions),
            option_count=sum(len(decision.options) for decision in self.decisions),
            stage_count=len({normalize_name(decision.stage) for decision in self.decisions}),
            axis_count=len(self.axes),
            decisions_requiring_designation_check=sum(
                decision.requires_designation_check for decision in self.decisions
            ),
            sourced_decision_count=sum(bool(decision.source_refs) for decision in self.decisions),
            referenced_source_count=len(self.sources),
        )


def load_winemaking_decisions() -> WinemakingDecisionRegistry:
    return WinemakingDecisionRegistry()
