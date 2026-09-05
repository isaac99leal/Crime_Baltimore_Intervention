"""Load explicit simulation priors for fermentation, élevage, and bottle aging.

These presets are model inputs. They are not claims about any real producer or wine.
"""
from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Any, TypeVar

from .schema import (
    AgingArchetype,
    ElevageProgram,
    ExtractionProgram,
    FaultRiskProfile,
    FermentationKinetics,
    FermentationProgram,
    FruitHandling,
    MalolacticProgram,
    NumericRange,
    SulfurOxygenProgram,
    VesselProgram,
    YeastProgram,
)

DATA_PATH = Path(__file__).resolve().parent / "data" / "simulation_priors.json"
T = TypeVar("T")


def _range(value: Any, *, unit: str = "") -> NumericRange:
    if isinstance(value, NumericRange):
        return value
    if value is None:
        return NumericRange(unit=unit)
    if isinstance(value, (int, float)):
        number = float(value)
        return NumericRange(low=number, typical=number, high=number, unit=unit)
    if isinstance(value, dict):
        return NumericRange(
            low=value.get("low"),
            typical=value.get("typical"),
            high=value.get("high"),
            unit=value.get("unit", unit),
        )
    raise TypeError(f"Cannot convert {type(value)!r} to NumericRange")


def _kwargs_for(cls: type[T], raw: dict[str, Any], range_fields: set[str]) -> dict[str, Any]:
    valid = {f.name for f in fields(cls)}
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in valid:
            continue
        out[key] = _range(value) if key in range_fields else value
    return out


def _fruit(raw: dict[str, Any]) -> FruitHandling:
    return FruitHandling(**_kwargs_for(
        FruitHandling,
        raw,
        {"cold_soak_days", "pre_ferment_skin_contact_hours", "must_settling_hours"},
    ))


def _yeast(raw: dict[str, Any]) -> YeastProgram:
    return YeastProgram(**_kwargs_for(YeastProgram, raw, {"target_yan_mg_l"}))


def _kinetics(raw: dict[str, Any]) -> FermentationKinetics:
    return FermentationKinetics(**_kwargs_for(
        FermentationKinetics,
        raw,
        {
            "vessel_volume_l", "pressure_bar", "start_temp_c", "peak_temp_c",
            "lag_hours", "active_days", "total_days", "target_residual_sugar_g_l",
        },
    ))


def _extraction(raw: dict[str, Any]) -> ExtractionProgram:
    return ExtractionProgram(**_kwargs_for(
        ExtractionProgram,
        raw,
        {
            "maceration_days", "pumpovers_per_day", "punchdowns_per_day",
            "delestage_count", "carbonic_fraction", "intracellular_days",
            "press_pressure_bar", "free_run_fraction",
        },
    ))


def _malolactic(raw: dict[str, Any]) -> MalolacticProgram:
    return MalolacticProgram(**_kwargs_for(MalolacticProgram, raw, {"temp_c", "duration_days"}))


def _sulfur_oxygen(raw: dict[str, Any]) -> SulfurOxygenProgram:
    return SulfurOxygenProgram(**_kwargs_for(
        SulfurOxygenProgram,
        raw,
        {
            "so2_at_crush_mg_l", "so2_post_ferment_mg_l",
            "free_so2_at_bottling_mg_l", "dissolved_oxygen_at_bottling_mg_l",
        },
    ))


def _fault_risk(raw: dict[str, Any]) -> FaultRiskProfile:
    return FaultRiskProfile(**_kwargs_for(FaultRiskProfile, raw, set()))


def _vessel(raw: dict[str, Any]) -> VesselProgram:
    return VesselProgram(**_kwargs_for(
        VesselProgram,
        raw,
        {"volume_l", "months", "new_oak_fraction"},
    ))


class SimulationPriors:
    """Validated, typed access to simulation-only process priors."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DATA_PATH
        doc = json.loads(self.path.read_text(encoding="utf-8"))
        self.schema_version = str(doc.get("schema_version", ""))
        self.purpose = str(doc.get("purpose", ""))

        self.aging_archetypes = {
            row["id"]: AgingArchetype(**row)
            for row in doc.get("aging_archetypes", [])
        }
        self.fermentation_programs = {
            row["id"]: self._fermentation(row)
            for row in doc.get("fermentation_presets", [])
        }
        self.elevage_programs = {
            row["id"]: self._elevage(row)
            for row in doc.get("elevage_presets", [])
        }
        self.validate()

    @staticmethod
    def _fermentation(row: dict[str, Any]) -> FermentationProgram:
        return FermentationProgram(
            id=row["id"],
            name=row["name"],
            style_family=row["style_family"],
            fruit=_fruit(row.get("fruit", {})),
            yeast=_yeast(row.get("yeast", {})),
            kinetics=_kinetics(row.get("kinetics", {})),
            extraction=_extraction(row.get("extraction", {})),
            malolactic=_malolactic(row.get("malolactic", {})),
            sulfur_oxygen=_sulfur_oxygen(row.get("sulfur_oxygen", {})),
            fault_risk=_fault_risk(row.get("fault_risk", {})),
            source_ids=list(row.get("source_ids", [])),
            is_simulation_prior=True,
        )

    @staticmethod
    def _elevage(row: dict[str, Any]) -> ElevageProgram:
        kwargs = _kwargs_for(
            ElevageProgram,
            row,
            {
                "total_months", "gross_lees_months", "fine_lees_months",
                "batonnage_per_month", "racking_count", "topping_frequency_days",
                "filtration_microns",
            },
        )
        kwargs["vessels"] = [_vessel(v) for v in row.get("vessels", [])]
        kwargs["is_simulation_prior"] = True
        return ElevageProgram(**kwargs)

    def validate(self) -> None:
        if len(self.aging_archetypes) != len(set(self.aging_archetypes)):
            raise ValueError("Duplicate aging archetype IDs")
        if len(self.fermentation_programs) != len(set(self.fermentation_programs)):
            raise ValueError("Duplicate fermentation program IDs")
        if len(self.elevage_programs) != len(set(self.elevage_programs)):
            raise ValueError("Duplicate élevage program IDs")

        range_objects: list[NumericRange] = []
        for program in self.fermentation_programs.values():
            for obj in (
                program.fruit, program.yeast, program.kinetics, program.extraction,
                program.malolactic, program.sulfur_oxygen,
            ):
                for f in fields(obj):
                    value = getattr(obj, f.name)
                    if isinstance(value, NumericRange):
                        range_objects.append(value)
        for program in self.elevage_programs.values():
            for f in fields(program):
                value = getattr(program, f.name)
                if isinstance(value, NumericRange):
                    range_objects.append(value)
            for vessel in program.vessels:
                for f in fields(vessel):
                    value = getattr(vessel, f.name)
                    if isinstance(value, NumericRange):
                        range_objects.append(value)

        errors = [error for r in range_objects for error in r.validate()]
        if errors:
            raise ValueError("Invalid simulation prior ranges: " + "; ".join(errors[:10]))

    def stats(self) -> dict[str, int]:
        return {
            "aging_archetypes": len(self.aging_archetypes),
            "fermentation_programs": len(self.fermentation_programs),
            "elevage_programs": len(self.elevage_programs),
        }
