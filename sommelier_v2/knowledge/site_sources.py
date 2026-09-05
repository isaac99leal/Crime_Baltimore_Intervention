"""Registry of bulk named-vineyard and parcel source systems.

This module does not create vineyard claims. It records where authoritative or
institutional site identities and boundaries can be ingested from. Legal wine
authorization stays in the protected-origin specification layer.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data" / "named_site_sources.json"


@dataclass(frozen=True)
class NamedSiteSource:
    id: str
    country: str
    region: str
    authority: str
    unit_types: tuple[str, ...]
    coverage_status: str
    source_url: str
    legal_claim_authority: bool = False
    reported_named_units: int | None = None
    minimum_reported_named_units: int | None = None
    reported_parcels: int | None = None
    notes: str = ""


class NamedSiteSourceRegistry:
    def __init__(self, data_path: Path | None = None) -> None:
        path = data_path or DATA_PATH
        doc = json.loads(path.read_text(encoding="utf-8"))
        rows = doc.get("sources", [])
        if not isinstance(rows, list):
            raise ValueError("named_site_sources.json sources must be a list")

        sources: list[NamedSiteSource] = []
        seen: set[str] = set()
        for row in rows:
            source_id = str(row.get("id") or "").strip()
            if not source_id:
                raise ValueError("Named-site source is missing an id")
            if source_id in seen:
                raise ValueError(f"Duplicate named-site source id: {source_id}")
            seen.add(source_id)

            url = str(row.get("source_url") or "").strip()
            if not url.startswith(("https://", "http://")):
                raise ValueError(f"{source_id} must have an HTTP(S) source URL")

            reported = row.get("reported_named_units")
            minimum = row.get("minimum_reported_named_units")
            parcels = row.get("reported_parcels")
            for name, value in (
                ("reported_named_units", reported),
                ("minimum_reported_named_units", minimum),
                ("reported_parcels", parcels),
            ):
                if value is not None and int(value) < 0:
                    raise ValueError(f"{source_id} {name} cannot be negative")

            sources.append(
                NamedSiteSource(
                    id=source_id,
                    country=str(row.get("country") or ""),
                    region=str(row.get("region") or ""),
                    authority=str(row.get("authority") or ""),
                    unit_types=tuple(str(v) for v in row.get("unit_types", [])),
                    coverage_status=str(row.get("coverage_status") or "unknown"),
                    source_url=url,
                    legal_claim_authority=bool(row.get("legal_claim_authority", False)),
                    reported_named_units=int(reported) if reported is not None else None,
                    minimum_reported_named_units=int(minimum) if minimum is not None else None,
                    reported_parcels=int(parcels) if parcels is not None else None,
                    notes=str(row.get("notes") or ""),
                )
            )
        self.sources = tuple(sources)
        self._by_id = {source.id: source for source in self.sources}

    def get(self, source_id: str) -> NamedSiteSource | None:
        return self._by_id.get(source_id)

    def for_region(self, country: str, region: str) -> tuple[NamedSiteSource, ...]:
        c = country.strip().casefold()
        r = region.strip().casefold()
        return tuple(
            source
            for source in self.sources
            if source.country.strip().casefold() == c
            and source.region.strip().casefold() == r
        )

    def stats(self) -> dict[str, int]:
        return {
            "named_site_bulk_sources": len(self.sources),
            "official_or_institutional_bulk_sources": sum(
                "bulk_registry" in source.coverage_status for source in self.sources
            ),
            "sources_with_reported_named_units": sum(
                source.reported_named_units is not None
                or source.minimum_reported_named_units is not None
                for source in self.sources
            ),
            "sources_with_parcel_counts": sum(
                source.reported_parcels is not None for source in self.sources
            ),
        }
