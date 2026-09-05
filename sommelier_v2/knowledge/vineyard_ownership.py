"""Time-varying vineyard ownership and area observations.

This registry is deliberately separate from NamedSite identity and protected-origin
law. A vineyard can keep one stable identity while its owner, operated surface, or
source evidence changes over time.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .catalog import normalize_name

DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class VineyardOwnershipObservation:
    site_name: str
    country: str
    region: str
    owner: str
    area_ha: float | None
    ownership_status: str
    effective_as_of: str | None
    source_ids: tuple[str, ...]
    notes: str = ""


class VineyardOwnershipRegistry:
    """Load current/historical ownership observations without redefining sites."""

    def __init__(self, data_path: Path | None = None) -> None:
        paths = (
            [Path(data_path)]
            if data_path is not None
            else sorted(DATA_DIR.glob("vineyard_ownership_*.json"), key=lambda item: item.name)
        )
        self.sources: dict[str, dict] = {}
        self.observations: list[VineyardOwnershipObservation] = []

        for path in paths:
            if not path.exists():
                if data_path is not None:
                    raise FileNotFoundError(path)
                continue
            doc = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise ValueError(f"{path.name} must contain a JSON object")

            for source_id, raw_source in dict(doc.get("sources", {})).items():
                source = dict(raw_source)
                existing = self.sources.get(str(source_id))
                if existing is not None and existing != source:
                    raise ValueError(f"Conflicting vineyard-ownership source: {source_id}")
                self.sources[str(source_id)] = source

            for row in doc.get("observations", []):
                if not isinstance(row, dict):
                    continue
                source_ids = tuple(str(value) for value in row.get("source_ids", []))
                missing = [source_id for source_id in source_ids if source_id not in self.sources]
                if missing:
                    raise ValueError(
                        f"Ownership observation for {row.get('site_name')!r} references unknown sources: {missing}"
                    )
                area = row.get("area_ha")
                self.observations.append(
                    VineyardOwnershipObservation(
                        site_name=str(row.get("site_name") or ""),
                        country=str(row.get("country") or ""),
                        region=str(row.get("region") or ""),
                        owner=str(row.get("owner") or ""),
                        area_ha=None if area in (None, "") else float(area),
                        ownership_status=str(row.get("ownership_status") or "documented"),
                        effective_as_of=(
                            str(row["effective_as_of"]) if row.get("effective_as_of") else None
                        ),
                        source_ids=source_ids,
                        notes=str(row.get("notes") or ""),
                    )
                )

    def for_site(
        self,
        site_name: str,
        *,
        country: str | None = None,
        region: str | None = None,
    ) -> list[VineyardOwnershipObservation]:
        site_key = normalize_name(site_name)
        country_key = normalize_name(country or "")
        region_key = normalize_name(region or "")
        return [
            row
            for row in self.observations
            if normalize_name(row.site_name) == site_key
            and (not country or normalize_name(row.country) == country_key)
            and (not region or normalize_name(row.region) == region_key)
        ]

    def latest_for_site(
        self,
        site_name: str,
        *,
        country: str | None = None,
        region: str | None = None,
    ) -> VineyardOwnershipObservation | None:
        rows = self.for_site(site_name, country=country, region=region)
        if not rows:
            return None
        return max(rows, key=lambda row: row.effective_as_of or "")

    def stats(self) -> dict[str, int]:
        return {
            "vineyard_ownership_observations": len(self.observations),
            "vineyard_ownership_sources": len(self.sources),
            "vineyard_ownership_sites": len(
                {
                    (
                        normalize_name(row.country),
                        normalize_name(row.region),
                        normalize_name(row.site_name),
                    )
                    for row in self.observations
                }
            ),
        }
