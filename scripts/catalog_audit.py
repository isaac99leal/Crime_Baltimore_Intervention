#!/usr/bin/env python3
"""Audit the legacy wine knowledge catalog without importing the game UI."""
from __future__ import annotations

import ast
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "somm_simulator" / "data"


def _vintage_quality_counts() -> tuple[int, int, int, int]:
    path = ROOT / "somm_simulator" / "generators" / "wine_generator.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    table = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "VINTAGE_QUALITY":
                    table = ast.literal_eval(node.value)
                    break
        if table is not None:
            break
    if not isinstance(table, dict):
        return 0, 0, 0, 0
    years = [year for vintages in table.values() for year in vintages]
    return len(table), sum(len(v) for v in table.values()), min(years), max(years)


def main() -> None:
    grapes_doc = json.loads((DATA / "grapes.json").read_text(encoding="utf-8"))
    regions_doc = json.loads((DATA / "regions.json").read_text(encoding="utf-8"))

    grapes = grapes_doc.get("grapes", [])
    countries = regions_doc.get("regions", [])

    wine_regions = []
    sub_regions = []
    communes = []
    hierarchy_paths = []
    for country in countries:
        country_name = country.get("country", "")
        for region in country.get("wine_regions", []):
            wine_regions.append(region)
            hierarchy_paths.append((country_name, region.get("name", "")))
            for sub in region.get("sub_regions", []):
                sub_regions.append(sub)
                hierarchy_paths.append((country_name, region.get("name", ""), sub.get("name", "")))
                for commune in sub.get("communes", []):
                    communes.append(commune)
                    hierarchy_paths.append((country_name, region.get("name", ""), sub.get("name", ""), commune.get("name", "")))

    grape_names = [g.get("name", "").strip() for g in grapes if g.get("name")]
    aliases = [a.strip() for g in grapes for a in g.get("aliases", []) if isinstance(a, str) and a.strip()]
    grape_country_counts = Counter(g.get("origin_country", "Unknown") or "Unknown" for g in grapes)

    classification_systems = {
        item.get("classification_system", "").strip()
        for item in [*wine_regions, *communes]
        if item.get("classification_system", "").strip()
    }
    soil_types = {
        soil.strip()
        for commune in communes
        for soil in commune.get("soil_types", [])
        if isinstance(soil, str) and soil.strip()
    }
    referenced_grapes = {
        grape.strip()
        for item in [*wine_regions, *sub_regions, *communes]
        for field in ("primary_grapes", "allowed_grapes")
        for grape in item.get(field, [])
        if isinstance(grape, str) and grape.strip()
    }

    vintage_regions, vintage_cells, vintage_min, vintage_max = _vintage_quality_counts()

    result = {
        "varietals": len(grapes),
        "unique_varietal_names": len(set(grape_names)),
        "aliases": len(aliases),
        "unique_aliases": len(set(aliases)),
        "origin_countries_represented": len(grape_country_counts),
        "countries_in_region_hierarchy": len(countries),
        "wine_regions": len(wine_regions),
        "sub_regions": len(sub_regions),
        "communes_or_appellations": len(communes),
        "geographic_nodes_excluding_countries": len(wine_regions) + len(sub_regions) + len(communes),
        "unique_geographic_paths_excluding_countries": len(set(hierarchy_paths)),
        "classification_systems": len(classification_systems),
        "soil_terms": len(soil_types),
        "grape_names_referenced_by_regions": len(referenced_grapes),
        "vintage_region_tables": vintage_regions,
        "vintage_region_year_cells": vintage_cells,
        "earliest_explicit_vintage": vintage_min,
        "latest_explicit_vintage": vintage_max,
    }
    print("CATALOG_AUDIT=" + json.dumps(result, sort_keys=True))
    print("TOP_GRAPE_ORIGIN_COUNTRIES=" + json.dumps(grape_country_counts.most_common(15)))


if __name__ == "__main__":
    main()
