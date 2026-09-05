"""Authoritative product-specification document index.

This registry is deliberately separate from :mod:`legal_specs`. A document in
this index proves only that a regulator exposes a legal source for the GI. It
does not prove that Sommelier Simulator has parsed every production rule in that
document. Source-only records therefore cannot make a protected-origin wine
eligible.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .catalog import normalize_name

DATA_PATH = Path(__file__).resolve().parent / "data" / "legal_spec_source_index.json"
MANIFEST_PATH = Path(__file__).resolve().parent / "data" / "legal_spec_source_manifest.json"

COUNTRY_TO_CODE = {
    "Austria": "AT", "Belgium": "BE", "Bulgaria": "BG", "Croatia": "HR",
    "Cyprus": "CY", "Czech Republic": "CZ", "Czechia": "CZ", "France": "FR",
    "Germany": "DE", "Greece": "GR", "Hungary": "HU", "Italy": "IT",
    "Luxembourg": "LU", "Malta": "MT", "Netherlands": "NL", "Poland": "PL",
    "Portugal": "PT", "Romania": "RO", "Slovakia": "SK", "Slovenia": "SI",
    "Spain": "ES", "Sweden": "SE",
}


@dataclass(frozen=True)
class LegalSourceRecord:
    gi_identifier: str
    file_number: str
    protected_names: tuple[str, ...]
    countries: tuple[str, ...]
    gi_type: str | None
    status: str | None
    modification_date: str | None
    application_id: str | None
    product_specification_attachment_ids: tuple[str, ...]
    single_document_attachment_ids: tuple[str, ...]
    source_urls: tuple[str, ...]
    index_status: str

    @property
    def has_product_specification(self) -> bool:
        return bool(self.product_specification_attachment_ids)

    @property
    def has_authoritative_document(self) -> bool:
        return bool(self.product_specification_attachment_ids or self.single_document_attachment_ids)


class LegalSourceRegistry:
    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or DATA_PATH
        self.records: list[LegalSourceRecord] = []
        self._by_gi: dict[str, LegalSourceRecord] = {}
        self._by_name: dict[tuple[str, str], list[LegalSourceRecord]] = {}
        if not self.data_path.exists():
            return
        raw = json.loads(self.data_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("legal_spec_source_index.json must contain a list")
        for row in raw:
            if not isinstance(row, dict):
                continue
            record = LegalSourceRecord(
                gi_identifier=str(row.get("gi_identifier") or ""),
                file_number=str(row.get("file_number") or ""),
                protected_names=tuple(str(x) for x in row.get("protected_names", []) if str(x).strip()),
                countries=tuple(str(x) for x in row.get("countries", []) if str(x).strip()),
                gi_type=row.get("gi_type"),
                status=row.get("status"),
                modification_date=row.get("modification_date"),
                application_id=str(row.get("application_id")) if row.get("application_id") not in (None, "") else None,
                product_specification_attachment_ids=tuple(str(x) for x in row.get("product_specification_attachment_ids", []) if str(x).strip()),
                single_document_attachment_ids=tuple(str(x) for x in row.get("single_document_attachment_ids", []) if str(x).strip()),
                source_urls=tuple(str(x) for x in row.get("source_urls", []) if str(x).strip()),
                index_status=str(row.get("index_status") or "unknown"),
            )
            if not record.gi_identifier:
                continue
            self.records.append(record)
            self._by_gi[record.gi_identifier] = record
            for country in record.countries or ("",):
                for name in record.protected_names:
                    self._by_name.setdefault((normalize_name(country), normalize_name(name)), []).append(record)

    def by_gi_identifier(self, gi_identifier: str) -> LegalSourceRecord | None:
        return self._by_gi.get(gi_identifier)

    def find(self, name: str, *, country_code: str | None = None) -> tuple[LegalSourceRecord, ...]:
        key = normalize_name(name)
        if country_code:
            code = COUNTRY_TO_CODE.get(country_code, country_code)
            return tuple(self._by_name.get((normalize_name(code), key), []))
        matches: list[LegalSourceRecord] = []
        for (_, candidate), rows in self._by_name.items():
            if candidate == key:
                matches.extend(rows)
        return tuple(matches)

    def stats(self) -> dict[str, int]:
        countries = {country for record in self.records for country in record.countries}
        return {
            "legal_source_records": len(self.records),
            "legal_source_countries": len(countries),
            "legal_sources_with_product_specification": sum(r.has_product_specification for r in self.records),
            "legal_sources_with_single_document": sum(bool(r.single_document_attachment_ids) for r in self.records),
            "legal_sources_with_any_document": sum(r.has_authoritative_document for r in self.records),
        }
