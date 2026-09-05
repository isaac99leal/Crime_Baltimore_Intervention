"""National wine-grape classification evidence.

This registry records whether a grape is classified for wine production under a
national rule. It must not be used as a substitute for commercial cultivation
evidence or for an appellation-specific grape authorization.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .catalog import normalize_name

DATA_PATH = Path(__file__).resolve().parent / "data" / "national_variety_classifications_2026.json"


@dataclass(frozen=True)
class NationalVarietyClassification:
    country: str
    variety: str
    berry_color: str | None
    status: str
    effective_from: str | None
    source_ids: tuple[str, ...]
    marked_asterisk_in_2026_order: bool = False


class NationalVarietyClassificationRegistry:
    def __init__(self, data_path: Path | None = None) -> None:
        path = data_path or DATA_PATH
        doc = json.loads(path.read_text(encoding="utf-8"))
        self.sources = dict(doc.get("sources", {}))
        self.records: list[NationalVarietyClassification] = []
        self._index: dict[tuple[str, str], NationalVarietyClassification] = {}

        for row in doc.get("records", []):
            country = str(row.get("country") or "").strip()
            variety = str(row.get("variety") or "").strip()
            if not country or not variety:
                raise ValueError("National variety classification requires country and variety")
            source_ids = tuple(str(v) for v in row.get("source_ids", []))
            unknown = [source_id for source_id in source_ids if source_id not in self.sources]
            if unknown:
                raise ValueError(
                    f"{country}/{variety} references unknown sources: {unknown}"
                )
            record = NationalVarietyClassification(
                country=country,
                variety=variety,
                berry_color=(
                    str(row["berry_color"]).strip()
                    if row.get("berry_color") is not None
                    else None
                ),
                status=str(row.get("status") or "classified_wine_grape"),
                effective_from=(
                    str(row["effective_from"]) if row.get("effective_from") else None
                ),
                source_ids=source_ids,
                marked_asterisk_in_2026_order=bool(
                    row.get("marked_asterisk_in_2026_order", False)
                ),
            )
            key = (normalize_name(country), normalize_name(variety))
            if key in self._index:
                raise ValueError(f"Duplicate national variety classification: {country}/{variety}")
            self._index[key] = record
            self.records.append(record)

    def get(self, country: str, variety: str) -> NationalVarietyClassification | None:
        return self._index.get((normalize_name(country), normalize_name(variety)))

    def is_classified(self, country: str, variety: str) -> bool:
        return self.get(country, variety) is not None

    def for_country(self, country: str) -> tuple[NationalVarietyClassification, ...]:
        key = normalize_name(country)
        return tuple(
            record
            for record in self.records
            if normalize_name(record.country) == key
        )

    def stats(self) -> dict[str, int]:
        countries = {normalize_name(record.country) for record in self.records}
        return {
            "national_variety_classifications": len(self.records),
            "national_variety_classification_countries": len(countries),
            "national_variety_sources": len(self.sources),
        }
