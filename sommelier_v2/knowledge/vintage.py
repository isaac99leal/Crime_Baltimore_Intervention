"""Migration layer for the legacy scalar vintage table.

The legacy table contains a single region/year quality scalar. This module preserves
that value with explicit provenance. It does not invent weather, chemistry, or style
facts that are absent from the source data.
"""
from __future__ import annotations

import ast
from pathlib import Path

from .catalog import normalize_name
from .schema import Confidence, VintageKnowledge

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]
LEGACY_GENERATOR = REPO_ROOT / "somm_simulator" / "generators" / "wine_generator.py"


def load_legacy_vintage_knowledge(path: Path | None = None) -> list[VintageKnowledge]:
    source_path = path or LEGACY_GENERATOR
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    table: dict[tuple[str, str], dict[int, float]] | None = None

    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "VINTAGE_QUALITY"
            for target in node.targets
        ):
            candidate = ast.literal_eval(node.value)
            if isinstance(candidate, dict):
                table = candidate
            break

    if table is None:
        raise ValueError("VINTAGE_QUALITY table was not found")

    records: list[VintageKnowledge] = []
    for (country, region), vintages in table.items():
        gi_key = f"legacy-geo:{normalize_name(country).replace(' ', '-')}|{normalize_name(region).replace(' ', '-')}"
        for year, quality in vintages.items():
            records.append(
                VintageKnowledge(
                    id=f"vintage:{normalize_name(country).replace(' ', '-')}:{normalize_name(region).replace(' ', '-')}:{year}",
                    gi_id=gi_key,
                    year=int(year),
                    overall_quality=float(quality),
                    source_ids=["legacy_vintage_quality"],
                    confidence=Confidence.LOW,
                    style_tags=["legacy_scalar_quality_only"],
                )
            )
    return sorted(records, key=lambda v: (v.gi_id, v.year))


def vintage_stats(records: list[VintageKnowledge]) -> dict[str, int]:
    years = [record.year for record in records]
    return {
        "legacy_vintage_records": len(records),
        "legacy_vintage_regions": len({record.gi_id for record in records}),
        "earliest_legacy_vintage": min(years) if years else 0,
        "latest_legacy_vintage": max(years) if years else 0,
    }
