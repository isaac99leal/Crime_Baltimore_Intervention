"""Structured source-backed wine-process chemistry evidence.

The records in this registry are factual observations, published guides, ranges,
or mechanistic statements from technical institutes and peer-reviewed reviews.
They are not simulator coefficients. The separate model-evidence map identifies
which records justify the *direction and scope* of a simulation transform without
claiming that the transform's numeric coefficient was published by that source.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .catalog import normalize_name

DATA_DIR = Path(__file__).resolve().parent / "data" / "process_chemistry"


class ProcessChemistryEvidenceError(ValueError):
    """Raised when the process-chemistry evidence corpus violates provenance rules."""


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
class ChemistryEvidenceSource:
    id: str
    publisher: str
    title: str
    url: str
    jurisdiction: str
    kind: str
    accessed: str


@dataclass(frozen=True)
class ChemistryEvidenceRecord:
    id: str
    domain: str
    fact_type: str
    facts: tuple[str, ...]
    measurements: Mapping[str, Any]
    conditions: Mapping[str, Any]
    source_refs: tuple[str, ...]

    def measurement(self, name: str, default: Any = None) -> Any:
        return self.measurements.get(name, default)

    def condition(self, name: str, default: Any = None) -> Any:
        return self.conditions.get(name, default)


@dataclass(frozen=True)
class ChemistryEvidenceStats:
    source_count: int
    referenced_source_count: int
    record_count: int
    domain_count: int
    record_with_measurements_count: int
    record_with_conditions_count: int


@dataclass(frozen=True)
class ModelEvidenceLink:
    model_element: str
    record_ids: tuple[str, ...]
    scope_note: str


# This map is intentionally explicit. It documents evidence relevance but never
# imports published measurement values into a simulation coefficient.
MODEL_EVIDENCE_LINKS: tuple[ModelEvidenceLink, ...] = (
    ModelEvidenceLink(
        "fermentation_chemistry.molecular_so2_mg_l",
        ("chem-so2-ph-effectiveness", "chem-ph-stability"),
        "Supports the pH dependence of SO2 effectiveness; the simulator formula remains a model estimate.",
    ),
    ModelEvidenceLink(
        "fermentation_chemistry.white_juice_solids_risk",
        ("chem-white-juice-solids-turbidity",),
        "Supports non-monotonic juice-solids risk; the simulator curve is derived, not an AWRI equation.",
    ),
    ModelEvidenceLink(
        "fermentation_chemistry.nutrient_timing_effect",
        (
            "chem-yan-low-risk-guide",
            "chem-yan-h2s-growth-phase",
            "chem-h2s-late-phase",
            "chem-yan-excess-residual-risk",
        ),
        "Supports context- and timing-dependent nitrogen effects; exact risk weights are simulation priors.",
    ),
    ModelEvidenceLink(
        "fermentation_chemistry.post_fermentation_microbiological_risk",
        ("chem-brett-risk-window", "chem-so2-ph-effectiveness"),
        "Supports the post-AF/MLF risk window and pH-dependent SO2 protection; the risk score is derived.",
    ),
    ModelEvidenceLink(
        "fermentation_engine._risk_state",
        (
            "chem-yan-h2s-growth-phase",
            "chem-h2s-late-phase",
            "chem-fermentation-temperature-yeast-health",
            "chem-white-juice-solids-turbidity",
        ),
        "Supports directional H2S/stall relationships only, not the kinetic coefficients.",
    ),
    ModelEvidenceLink(
        "fermentation_engine.step_alcoholic_fermentation.va",
        ("chem-volatile-acidity", "chem-yan-excess-residual-risk"),
        "Supports VA as a process/fault-risk variable; the incremental VA equation is a simulator prior.",
    ),
)


class ProcessChemistryEvidenceRegistry:
    """Load and query source-backed process-chemistry records."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.sources: tuple[ChemistryEvidenceSource, ...] = ()
        self.records: tuple[ChemistryEvidenceRecord, ...] = ()
        self._source_index: dict[str, ChemistryEvidenceSource] = {}
        self._record_index: dict[str, ChemistryEvidenceRecord] = {}
        self._load_sources()
        self._load_records()
        self._validate_model_links()

    def _load_sources(self) -> None:
        sources: list[ChemistryEvidenceSource] = []
        seen: set[str] = set()
        files = _ordered_files("sources_pass")
        if not files:
            raise ProcessChemistryEvidenceError(
                f"No process-chemistry source files found in {self.data_dir}"
            )
        for path in files:
            doc = json.loads(path.read_text(encoding="utf-8"))
            for raw in doc.get("sources", []):
                source_id = str(raw.get("id", "")).strip()
                if not source_id or source_id in seen:
                    raise ProcessChemistryEvidenceError(
                        f"Missing or duplicate chemistry source id {source_id!r} in {path.name}"
                    )
                url = str(raw.get("url", "")).strip()
                if not url.startswith(("https://", "http://")):
                    raise ProcessChemistryEvidenceError(
                        f"Chemistry source {source_id} lacks an absolute URL"
                    )
                source = ChemistryEvidenceSource(
                    id=source_id,
                    publisher=str(raw.get("publisher", "")).strip(),
                    title=str(raw.get("title", "")).strip(),
                    url=url,
                    jurisdiction=str(raw.get("jurisdiction", "")).strip(),
                    kind=str(raw.get("kind", "")).strip(),
                    accessed=str(raw.get("accessed", "")).strip(),
                )
                if not source.publisher or not source.title or not source.kind:
                    raise ProcessChemistryEvidenceError(
                        f"Incomplete chemistry source metadata for {source_id}"
                    )
                seen.add(source_id)
                sources.append(source)
        self.sources = tuple(sources)
        self._source_index = {source.id: source for source in self.sources}

    def _load_records(self) -> None:
        records: list[ChemistryEvidenceRecord] = []
        seen: set[str] = set()
        files = _ordered_files("wine_chemistry_processes")
        if not files:
            raise ProcessChemistryEvidenceError(
                f"No process-chemistry records found in {self.data_dir}"
            )
        for path in files:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("schemaVersion") != 1:
                raise ProcessChemistryEvidenceError(
                    f"Unsupported chemistry schema in {path.name}"
                )
            for raw in doc.get("records", []):
                record_id = str(raw.get("id", "")).strip()
                if not record_id or record_id in seen:
                    raise ProcessChemistryEvidenceError(
                        f"Missing or duplicate chemistry record id {record_id!r}"
                    )
                fact_type = str(raw.get("factType", "")).strip()
                if normalize_name(fact_type) != normalize_name("source-backed"):
                    raise ProcessChemistryEvidenceError(
                        f"Chemistry record {record_id} must be explicitly source-backed; got {fact_type!r}"
                    )
                domain = str(raw.get("domain", "")).strip()
                facts_raw = raw.get("facts", [])
                if not domain or not isinstance(facts_raw, list) or not facts_raw:
                    raise ProcessChemistryEvidenceError(
                        f"Chemistry record {record_id} lacks domain/factual statements"
                    )
                facts = tuple(str(value).strip() for value in facts_raw if str(value).strip())
                if not facts:
                    raise ProcessChemistryEvidenceError(
                        f"Chemistry record {record_id} has no nonempty facts"
                    )
                source_refs = tuple(str(value).strip() for value in raw.get("sourceRefs", []) if str(value).strip())
                if not source_refs:
                    raise ProcessChemistryEvidenceError(
                        f"Chemistry record {record_id} has no source references"
                    )
                for source_ref in source_refs:
                    if source_ref not in self._source_index:
                        raise ProcessChemistryEvidenceError(
                            f"Chemistry record {record_id} references unknown source {source_ref}"
                        )
                measurements = raw.get("measurements", {})
                conditions = raw.get("conditions", {})
                if measurements is None:
                    measurements = {}
                if conditions is None:
                    conditions = {}
                if not isinstance(measurements, dict) or not isinstance(conditions, dict):
                    raise ProcessChemistryEvidenceError(
                        f"Chemistry record {record_id} measurements/conditions must be objects"
                    )
                record = ChemistryEvidenceRecord(
                    id=record_id,
                    domain=domain,
                    fact_type=fact_type,
                    facts=facts,
                    measurements=_freeze(measurements),
                    conditions=_freeze(conditions),
                    source_refs=source_refs,
                )
                records.append(record)
                seen.add(record_id)
        self.records = tuple(records)
        self._record_index = {record.id: record for record in self.records}

    def _validate_model_links(self) -> None:
        for link in MODEL_EVIDENCE_LINKS:
            if not link.model_element or not link.record_ids or not link.scope_note:
                raise ProcessChemistryEvidenceError("Incomplete model-evidence link")
            missing = [record_id for record_id in link.record_ids if record_id not in self._record_index]
            if missing:
                raise ProcessChemistryEvidenceError(
                    f"Model-evidence link {link.model_element} references missing records {missing}"
                )

    def source(self, source_id: str) -> ChemistryEvidenceSource | None:
        return self._source_index.get(source_id)

    def record(self, record_id: str) -> ChemistryEvidenceRecord | None:
        return self._record_index.get(record_id)

    def by_domain(self, domain: str) -> tuple[ChemistryEvidenceRecord, ...]:
        key = normalize_name(domain)
        return tuple(record for record in self.records if normalize_name(record.domain) == key)

    def by_source(self, source_id: str) -> tuple[ChemistryEvidenceRecord, ...]:
        return tuple(record for record in self.records if source_id in record.source_refs)

    def model_evidence(self, model_element: str) -> tuple[ChemistryEvidenceRecord, ...]:
        link = next(
            (link for link in MODEL_EVIDENCE_LINKS if link.model_element == model_element),
            None,
        )
        if link is None:
            return ()
        return tuple(self._record_index[record_id] for record_id in link.record_ids)

    def model_evidence_note(self, model_element: str) -> str | None:
        link = next(
            (link for link in MODEL_EVIDENCE_LINKS if link.model_element == model_element),
            None,
        )
        return link.scope_note if link is not None else None

    def referenced_sources(self) -> tuple[ChemistryEvidenceSource, ...]:
        ids = sorted({source_ref for record in self.records for source_ref in record.source_refs})
        return tuple(self._source_index[source_id] for source_id in ids)

    def stats(self) -> ChemistryEvidenceStats:
        return ChemistryEvidenceStats(
            source_count=len(self.sources),
            referenced_source_count=len(self.referenced_sources()),
            record_count=len(self.records),
            domain_count=len({normalize_name(record.domain) for record in self.records}),
            record_with_measurements_count=sum(bool(record.measurements) for record in self.records),
            record_with_conditions_count=sum(bool(record.conditions) for record in self.records),
        )

    def assert_not_simulation_coefficient(self, record_id: str, measurement_name: str) -> None:
        """Fail loudly when code tries to treat evidence as a hidden model coefficient.

        Callers may use a published measurement as an explicit guide, threshold,
        or displayed factual value when its scope is respected. They must not
        silently claim the value is the simulator coefficient itself.
        """
        record = self.record(record_id)
        if record is None:
            raise ProcessChemistryEvidenceError(f"Unknown chemistry record {record_id!r}")
        if measurement_name not in record.measurements:
            raise ProcessChemistryEvidenceError(
                f"Record {record_id!r} has no measurement {measurement_name!r}"
            )
        raise ProcessChemistryEvidenceError(
            f"{record_id}.{measurement_name} is source-backed evidence, not a simulator coefficient."
        )


def load_process_chemistry_evidence() -> ProcessChemistryEvidenceRegistry:
    return ProcessChemistryEvidenceRegistry()
