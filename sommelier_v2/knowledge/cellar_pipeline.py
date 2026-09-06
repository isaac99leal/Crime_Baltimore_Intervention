"""Deterministic handoff across cellar process engines.

The lower-level knowledge modules intentionally keep fermentation, extraction,
maturation, packaging, legal authority, and qualitative decision matrices
separate. This module provides one explicit execution path across those stages
without weakening the provenance rules used by each layer.

No missing analytical value is replaced with zero. In particular, SO2 at the
start of maturation and immediately before packaging must come from an explicit
measurement/plan value or from an already explicit upstream addition target.
Likewise, maturation dissolved oxygen is never promoted to a pre-bottling
measurement automatically because racking, transfer, filtration, and bottling
can change oxygen exposure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .decision_runtime import (
    DecisionRuntimeInputs,
    DecisionRuntimeResult,
    apply_winemaking_decisions,
)
from .extraction_process import ExtractionPlan, ExtractionResult, simulate_extraction
from .fermentation_process import FermentationPlan, FermentationResult, MustComposition, run_fermentation
from .legal_specs import LegalWineSpec
from .maturation_process import MaturationInput, MaturationPlan, MaturationResult, simulate_maturation
from .packaging import PackagingAssessment, PackagingPlan, assess_packaging


class CellarPipelineConstraintError(ValueError):
    """Raised when an inter-stage handoff would require an invented value."""


@dataclass(frozen=True)
class CellarPipelinePlan:
    """Select which physical process layers are executed.

    Extraction and maturation are opt-in because a wine can legitimately skip
    either modeled layer, and because silently treating every fermentation as
    skin-contact or every wine as undergoing élevage would create false states.
    Packaging assessment is always performed at the end of the pipeline.
    """

    run_extraction: bool = False
    run_maturation: bool = False


@dataclass(frozen=True)
class CellarHandoffInputs:
    """Explicit measurements needed between otherwise separate engines."""

    # Used only when the maturation stage runs. If omitted, an explicit
    # post-fermentation SO2 target on FermentationPlan may supply the value.
    maturation_free_so2_mg_l: float | None = None
    maturation_dissolved_oxygen_mg_l: float | None = None

    # Required when maturation runs without the extraction layer. Supplying
    # these while extraction is executed is rejected to prevent competing
    # provenance for the same modeled structural state.
    maturation_tannin_index: float | None = None
    maturation_phenolic_index: float | None = None
    maturation_anthocyanin_index: float | None = None

    # A later pre-packaging measurement can supersede upstream SO2. If omitted,
    # the pipeline may use the final maturation SO2, or an explicit
    # post-fermentation SO2 target when maturation was skipped.
    packaging_free_so2_mg_l: float | None = None

    def __post_init__(self) -> None:
        for name, value, high in (
            ("maturation_free_so2_mg_l", self.maturation_free_so2_mg_l, 300.0),
            ("maturation_dissolved_oxygen_mg_l", self.maturation_dissolved_oxygen_mg_l, 20.0),
            ("packaging_free_so2_mg_l", self.packaging_free_so2_mg_l, 300.0),
        ):
            if value is not None and not 0.0 <= value <= high:
                raise CellarPipelineConstraintError(f"{name} must be within 0..{high:g}")
        for name, value in (
            ("maturation_tannin_index", self.maturation_tannin_index),
            ("maturation_phenolic_index", self.maturation_phenolic_index),
            ("maturation_anthocyanin_index", self.maturation_anthocyanin_index),
        ):
            if value is not None and not 0.0 <= value <= 1.0:
                raise CellarPipelineConstraintError(f"{name} must be within 0..1")


@dataclass(frozen=True)
class CellarPipelineResult:
    decision_runtime: DecisionRuntimeResult
    fermentation: FermentationResult
    extraction: ExtractionResult | None
    maturation: MaturationResult | None
    packaging: PackagingAssessment
    final_ph: float
    packaging_free_so2_mg_l: float
    warnings: tuple[str, ...] = ()


_EXTRACTION_DECISIONS = frozenset({"cap-management", "maceration-duration", "press-fraction"})
_MATURATION_DECISIONS = frozenset(
    {
        "maturation-duration",
        "maturation-vessel",
        "new-oak-percentage",
        "oak-species",
        "oak-toast",
        "barrel-age",
        "lees-contact",
        "batonnage",
        "topping-ullage",
        "micro-oxygenation",
    }
)


def _final_ph(must: MustComposition, fermentation: FermentationResult) -> float:
    if fermentation.malolactic_history:
        return fermentation.malolactic_history[-1].ph
    return must.ph


def _resolve_maturation_so2(
    runtime: DecisionRuntimeResult,
    handoff: CellarHandoffInputs,
) -> float:
    if handoff.maturation_free_so2_mg_l is not None:
        return handoff.maturation_free_so2_mg_l
    explicit_plan_value = runtime.fermentation_plan.post_fermentation_free_so2_mg_l
    if explicit_plan_value is not None:
        return explicit_plan_value
    raise CellarPipelineConstraintError(
        "Maturation requires explicit free SO2 at the handoff; neither "
        "maturation_free_so2_mg_l nor post_fermentation_free_so2_mg_l was supplied."
    )


def _maturation_structure(
    extraction: ExtractionResult | None,
    handoff: CellarHandoffInputs,
) -> tuple[float, float, float]:
    explicit = (
        handoff.maturation_tannin_index,
        handoff.maturation_phenolic_index,
        handoff.maturation_anthocyanin_index,
    )
    if extraction is not None:
        if any(value is not None for value in explicit):
            raise CellarPipelineConstraintError(
                "Explicit maturation structural indices cannot be supplied when the extraction engine "
                "already provides those indices."
            )
        return extraction.tannin_index, extraction.phenolic_index, extraction.anthocyanin_index
    if any(value is None for value in explicit):
        raise CellarPipelineConstraintError(
            "Maturation without extraction requires explicit tannin, phenolic, and anthocyanin indices; "
            "missing structure is not interpreted as zero."
        )
    tannin, phenolic, anthocyanin = explicit
    assert tannin is not None and phenolic is not None and anthocyanin is not None
    return tannin, phenolic, anthocyanin


def _resolve_packaging_so2(
    runtime: DecisionRuntimeResult,
    maturation: MaturationResult | None,
    handoff: CellarHandoffInputs,
) -> float:
    if handoff.packaging_free_so2_mg_l is not None:
        return handoff.packaging_free_so2_mg_l
    if maturation is not None:
        return maturation.final_state.free_so2_mg_l
    explicit_plan_value = runtime.fermentation_plan.post_fermentation_free_so2_mg_l
    if explicit_plan_value is not None:
        return explicit_plan_value
    raise CellarPipelineConstraintError(
        "Packaging requires an explicit free SO2 value when maturation is skipped; provide "
        "packaging_free_so2_mg_l or post_fermentation_free_so2_mg_l."
    )


def run_cellar_pipeline(
    *,
    must: MustComposition,
    fermentation_plan: FermentationPlan,
    selections: Mapping[str, str] | None = None,
    runtime_inputs: DecisionRuntimeInputs = DecisionRuntimeInputs(),
    extraction_plan: ExtractionPlan = ExtractionPlan(),
    maturation_plan: MaturationPlan = MaturationPlan(duration_days=0.0),
    packaging_plan: PackagingPlan = PackagingPlan(),
    pipeline_plan: CellarPipelinePlan = CellarPipelinePlan(),
    handoff: CellarHandoffInputs = CellarHandoffInputs(),
    protected_designation: bool = False,
    legal_spec: LegalWineSpec | None = None,
    legal_confirmations: Mapping[str, bool] | None = None,
) -> CellarPipelineResult:
    """Run one wine lot through explicit cellar process stages.

    The function executes the decision/legal gate first, then fermentation,
    optional extraction, optional maturation, and finally packaging assessment.
    It does not assemble a commercial label or run bottle aging; those remain
    separate downstream layers.
    """
    selected = selections or {}
    if not pipeline_plan.run_extraction and _EXTRACTION_DECISIONS.intersection(selected):
        raise CellarPipelineConstraintError(
            "Extraction decisions were selected while run_extraction=False. Enable the extraction stage "
            "rather than discarding configured cap, maceration, or press operations."
        )
    if not pipeline_plan.run_maturation and _MATURATION_DECISIONS.intersection(selected):
        raise CellarPipelineConstraintError(
            "Maturation decisions were selected while run_maturation=False. Enable the maturation stage "
            "rather than discarding configured élevage operations."
        )

    runtime = apply_winemaking_decisions(
        selected,
        must=must,
        fermentation_plan=fermentation_plan,
        packaging_plan=packaging_plan,
        extraction_plan=extraction_plan,
        maturation_plan=maturation_plan,
        runtime_inputs=runtime_inputs,
        protected_designation=protected_designation,
        legal_spec=legal_spec,
        legal_confirmations=legal_confirmations,
    )

    fermentation = run_fermentation(runtime.must, runtime.fermentation_plan)
    warnings: list[str] = list(fermentation.warnings)

    extraction: ExtractionResult | None = None
    if pipeline_plan.run_extraction:
        extraction = simulate_extraction(
            fermentation.alcoholic_history,
            runtime.extraction_plan,
            whole_cluster_fraction=runtime.fermentation_plan.alcoholic_params.whole_cluster_fraction,
            source_extraction_potential=runtime.must.source_extraction_potential,
        )
        warnings.extend(extraction.warnings)

    final_ph = _final_ph(runtime.must, fermentation)

    maturation: MaturationResult | None = None
    if pipeline_plan.run_maturation:
        free_so2 = _resolve_maturation_so2(runtime, handoff)
        tannin, phenolic, anthocyanin = _maturation_structure(extraction, handoff)
        maturation_input = MaturationInput(
            ph=final_ph,
            free_so2_mg_l=free_so2,
            tannin_index=tannin,
            phenolic_index=phenolic,
            anthocyanin_index=anthocyanin,
            microbial_risk=fermentation.post_fermentation_microbiological_risk,
            dissolved_oxygen_mg_l=handoff.maturation_dissolved_oxygen_mg_l,
        )
        maturation = simulate_maturation(maturation_input, runtime.maturation_plan)
        warnings.extend(maturation.warnings)

    packaging_so2 = _resolve_packaging_so2(runtime, maturation, handoff)
    packaging = assess_packaging(
        ph=final_ph,
        free_so2_mg_l=packaging_so2,
        plan=runtime.packaging_plan,
    )
    warnings.extend(packaging.warnings)

    return CellarPipelineResult(
        decision_runtime=runtime,
        fermentation=fermentation,
        extraction=extraction,
        maturation=maturation,
        packaging=packaging,
        final_ph=final_ph,
        packaging_free_so2_mg_l=packaging_so2,
        warnings=tuple(warnings),
    )
