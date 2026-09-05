#!/usr/bin/env python3
"""Refresh external wine-knowledge snapshots from public source registries.

This script intentionally uses only the Python standard library. It keeps source
identity separate from biological identity: acreage rows prove cultivation of a
name, not that every spelling is a distinct genotype.
"""
from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "sommelier_v2" / "knowledge" / "data"
DATA.mkdir(parents=True, exist_ok=True)

ADELAIDE_XLSX = "https://economics.adelaide.edu.au/wine-economics/ua/media/476/varieties_2000_to_2023.xlsx"
ADELAIDE_DOI = "https://doi.org/10.25909/32870405.v1"
EAMBROSIA = "https://webgate.ec.europa.eu/eambrosia-api/api/v1/geographical-indications"

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def request_bytes(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SommelierSimulatorKnowledgeSync/2.0 (+research dataset refresh)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _shared_strings(book: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(book.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall(f"{{{MAIN}}}si"):
        values.append("".join(node.text or "" for node in item.iter(f"{{{MAIN}}}t")))
    return values


def _sheet_path(book: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(book.read("xl/workbook.xml"))
    rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    relation_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    sheets = workbook.find(f"{{{MAIN}}}sheets")
    if sheets is None:
        raise ValueError("Workbook has no sheets")
    for sheet in sheets:
        if sheet.attrib.get("name") == sheet_name:
            rid = sheet.attrib[f"{{{DOC_REL}}}id"]
            target = relation_map[rid].lstrip("/")
            return target if target.startswith("xl/") else "xl/" + target
    raise KeyError(f"Sheet not found: {sheet_name}")


def _column_index(reference: str) -> int:
    match = re.match(r"[A-Z]+", reference)
    if not match:
        raise ValueError(reference)
    result = 0
    for char in match.group(0):
        result = result * 26 + ord(char) - 64
    return result - 1


def xlsx_rows(payload: bytes, sheet_name: str) -> list[list[object]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as book:
        shared = _shared_strings(book)
        root = ET.fromstring(book.read(_sheet_path(book, sheet_name)))
        sheet_data = root.find(f"{{{MAIN}}}sheetData")
        if sheet_data is None:
            return []
        rows: list[list[object]] = []
        for row in sheet_data.findall(f"{{{MAIN}}}row"):
            cells: dict[int, object] = {}
            for cell in row.findall(f"{{{MAIN}}}c"):
                index = _column_index(cell.attrib["r"])
                cell_type = cell.attrib.get("t")
                value_node = cell.find(f"{{{MAIN}}}v")
                if cell_type == "s" and value_node is not None:
                    value: object = shared[int(value_node.text or "0")]
                elif cell_type == "inlineStr":
                    value = "".join(node.text or "" for node in cell.iter(f"{{{MAIN}}}t"))
                elif value_node is not None:
                    raw = value_node.text or ""
                    try:
                        value = float(raw)
                    except ValueError:
                        value = raw
                else:
                    value = ""
                cells[index] = value
            if cells:
                rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
        return rows


def number(value: object) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"{float(value):.10g}"
    except (TypeError, ValueError):
        return ""


def write_adelaide(payload: bytes) -> dict[str, int]:
    world = xlsx_rows(payload, "World alphabetical")
    countries = xlsx_rows(payload, "All countries")
    if not world or normalize(str(world[0][0])) != "prime":
        raise ValueError("Unexpected Adelaide world sheet layout")
    if not countries or normalize(str(countries[0][0])) != "country":
        raise ValueError("Unexpected Adelaide country sheet layout")

    world_path = DATA / "adelaide_world_varieties_2000_2023.csv"
    with world_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["prime", "area_2000_ha", "area_2010_ha", "area_2016_ha", "area_2023_ha"])
        for row in world[1:]:
            row = list(row) + [""] * (5 - len(row))
            writer.writerow([str(row[0]).strip(), *(number(v) for v in row[1:5])])

    country_path = DATA / "adelaide_country_varieties_2000_2023.csv"
    with country_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["country", "prime", "area_2000_ha", "area_2010_ha", "area_2016_ha", "area_2023_ha"])
        for row in countries[1:]:
            row = list(row) + [""] * (6 - len(row))
            writer.writerow([str(row[0]).strip(), str(row[1]).strip(), *(number(v) for v in row[2:6])])

    positive_2023 = 0
    tiny_2023 = 0
    micro_2023 = 0
    for row in world[1:]:
        value = row[4] if len(row) > 4 else ""
        try:
            area = float(value)
        except (TypeError, ValueError):
            continue
        if area > 0:
            positive_2023 += 1
            if area <= 1:
                tiny_2023 += 1
            if area <= 5:
                micro_2023 += 1

    real_country_labels = {
        str(row[0]).strip() for row in countries[1:]
        if row and str(row[0]).strip() and not str(row[0]).strip().casefold().startswith("missing")
    }
    return {
        "world_variety_rows": len(world) - 1,
        "country_variety_rows": len(countries) - 1,
        "country_labels": len(real_country_labels),
        "positive_area_2023": positive_2023,
        "tiny_area_le_1ha_2023": tiny_2023,
        "micro_area_le_5ha_2023": micro_2023,
    }


def fetch_eambrosia() -> list[dict[str, object]]:
    params = urllib.parse.urlencode({
        "modifiedOnFrom": "1900-01-01T00:00:00.000Z",
        "modifiedOnTo": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    })
    payload = request_bytes(EAMBROSIA + "?" + params, timeout=240)
    raw = json.loads(payload.decode("utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Unexpected eAmbrosia response")
    wine: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in raw:
        if not isinstance(row, dict) or row.get("productType") != "WINE":
            continue
        identifier = str(row.get("giIdentifier") or "")
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)
        wine.append({
            "gi_identifier": identifier,
            "protected_names": row.get("protectedNames") or [],
            "file_number": row.get("fileNumber"),
            "countries": row.get("countries") or [],
            "gi_type": row.get("giType"),
            "status": row.get("status"),
            "eu_protection_date": row.get("euProtectionDate"),
            "modification_date": row.get("modificationDate"),
            "third_country": bool(row.get("thirdCountryFlag")),
            "removed": bool(row.get("removedFlag")),
        })
    wine.sort(key=lambda r: (str(r.get("countries")), str(r.get("protected_names"))))
    (DATA / "eambrosia_wine_gis.json").write_text(
        json.dumps(wine, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return wine


def main() -> None:
    workbook = request_bytes(ADELAIDE_XLSX, timeout=240)
    acreage_stats = write_adelaide(workbook)
    sync_stats: dict[str, object] = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "adelaide": acreage_stats,
        "sources": {
            "adelaide_xlsx": ADELAIDE_XLSX,
            "adelaide_doi": ADELAIDE_DOI,
            "eambrosia_api": EAMBROSIA,
        },
    }
    try:
        wine_gis = fetch_eambrosia()
        sync_stats["eambrosia_wine_gis"] = len(wine_gis)
    except Exception as exc:  # acreage sync remains useful if EU service is unavailable
        sync_stats["eambrosia_error"] = f"{type(exc).__name__}: {exc}"
        print("WARNING: eAmbrosia refresh failed:", exc)

    (DATA / "external_sync_manifest.json").write_text(
        json.dumps(sync_stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("EXTERNAL_KNOWLEDGE_SYNC=" + json.dumps(sync_stats, sort_keys=True))


if __name__ == "__main__":
    main()
