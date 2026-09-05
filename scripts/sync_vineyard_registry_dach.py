#!/usr/bin/env python3
"""Materialize authoritative German/Austrian named-vineyard registries.

Sources are deliberately kept at their real evidence date:
- Land Niederösterreich current OGD WFS for Rieden/Subrieden.
- Landwirtschaftskammer Rheinland-Pfalz official "Ernte 2024" Weinlagen
  register PDF for Einzellagen. The PDF is a dated official register snapshot,
  not a claim that every row is unchanged in 2026.

No site-level soil, grape, slope, elevation, ownership, or geometry facts are
inferred when the source does not provide them.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "sommelier_v2" / "knowledge" / "data"
RLP_OUT = DATA_DIR / "named_sites_expansion_2026_germany_rlp.json"
NOE_OUT = DATA_DIR / "named_sites_expansion_2026_austria_noe.json"
MANIFEST_OUT = DATA_DIR / "vineyard_registry_dach_sync_manifest.json"

RLP_SOURCE_PAGE = "https://www.lwk-rlp.de/weinbau/rebflaechen/weinlagen"
RLP_PDF_URL = "https://www.lwk-rlp.de/fileadmin/lwk/Weinbau/PDF/Weinlagen_Internet_2024.pdf"
NOE_SOURCE_PAGE = "https://www.noe.gv.at/noe/OGD_Detailseite.html?id=a22e57c2-bbb0-4fb9-a731-b7f675e48476&print=true"
NOE_WFS_URL = "https://sdi.noe.gv.at/at.gv.noe.geoserver/OGD/wfs"
UA = "SommelierSimulatorV2/1.0 (+https://github.com/isaac99leal/Crime_Baltimore_Intervention)"


def _slug(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "unknown"


def _text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    value = str(value).strip()
    return value or None


def _download(url: str, *, accept: str = "*/*", attempts: int = 4) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Could not fetch {url}: {last_error}")


def _request_json(base_url: str, params: Mapping[str, str], attempts: int = 4) -> dict[str, Any]:
    url = base_url + ("&" if "?" in base_url else "?") + urllib.parse.urlencode(params)
    payload = _download(url, accept="application/json", attempts=attempts)
    doc = json.loads(payload)
    if not isinstance(doc, dict):
        raise ValueError("Expected JSON object")
    return doc


def _features(base_url: str, type_name: str, version: str = "2.0.0") -> list[dict[str, Any]]:
    type_key = "typeName" if version.startswith("1.") else "typeNames"
    doc = _request_json(base_url, {
        "service": "WFS",
        "version": version,
        "request": "GetFeature",
        type_key: type_name,
        "count": "10000",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
    })
    rows = doc.get("features")
    if not isinstance(rows, list):
        raise ValueError(f"{type_name}: WFS response has no feature list")
    return [row for row in rows if isinstance(row, dict)]


def _properties(feature: Mapping[str, Any]) -> dict[str, Any]:
    raw = feature.get("properties", {})
    return dict(raw) if isinstance(raw, Mapping) else {}


def _noe_records(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not features:
        raise ValueError("Niederösterreich WFS returned zero features")
    records: dict[str, dict[str, Any]] = {}

    for feature in features:
        props = _properties(feature)
        ried = _text(props.get("WEINBAURIEDE1"))
        subried = _text(props.get("WEINBAURIEDE2"))
        flur = _text(props.get("WEINBAUFLUR"))
        kg = _text(props.get("KGNAME"))
        municipality = _text(props.get("PGNAME"))
        status = _text(props.get("UMSETZUNG_STATUS"))
        updated = _text(props.get("LASTUPDATE"))
        if not ried:
            continue

        locality = kg or municipality or flur or "Niederösterreich"
        parent = flur or kg or municipality or "Niederösterreich"
        main_id = f"site:austria:niederoesterreich:{_slug(locality)}:ried:{_slug(ried)}"
        records.setdefault(main_id, {
            "id": main_id,
            "name": ried,
            "country": "Austria",
            "region": "Niederösterreich",
            "parent": parent,
            "commune": kg or municipality,
            "site_type": "ried",
            "classification": "Ried",
            "legal_status": "official_verordnete_ried" if (status or "").casefold() == "verordnung" else "official_ried_dataset",
            "source_ids": ["noe_rieden_wfs_2026"],
            "geometry_source_id": "noe_rieden_wfs_2026",
            "notes": f"Land Niederösterreich OGD; status={status or 'unknown'}{'; last update=' + updated if updated else ''}.",
        })

        if subried and subried.casefold() not in {"keine subriede", "keine subried", "none", "-"}:
            sub_id = f"{main_id}:subried:{_slug(subried)}"
            records.setdefault(sub_id, {
                "id": sub_id,
                "name": subried,
                "country": "Austria",
                "region": "Niederösterreich",
                "parent": ried,
                "parent_site_id": main_id,
                "commune": kg or municipality,
                "site_type": "subried",
                "classification": "Subriede",
                "legal_status": "official_verordnete_subried" if (status or "").casefold() == "verordnung" else "official_subried_dataset",
                "source_ids": ["noe_rieden_wfs_2026"],
                "geometry_source_id": "noe_rieden_wfs_2026",
                "notes": f"Land Niederösterreich OGD; status={status or 'unknown'}{'; last update=' + updated if updated else ''}.",
            })

    if not records:
        keys = sorted(_properties(features[0]))
        raise ValueError(f"Niederösterreich WFS yielded no Rieden; first property keys={keys}")
    return sorted(records.values(), key=lambda row: (row.get("commune") or "", row["site_type"], row["name"].casefold()))


def _pdf_to_layout_text(pdf_bytes: bytes) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "weinlagen.pdf"
        pdf_path.write_bytes(pdf_bytes)
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pdftotext failed: {result.stderr.strip()}")
        return result.stdout


def _rlp_records_from_pdf(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Parse the fixed-column official LWK Weinlagen register.

    `pdftotext -layout` preserves the table columns. Rows begin with a six-digit
    Lagennummer. Header context supplies Anbaugebiet/Bereich/Großlage.
    """
    content = _pdf_to_layout_text(pdf_bytes)
    anbaugebiet: str | None = None
    bereich: str | None = None
    grosslage: str | None = None
    records: dict[str, dict[str, Any]] = {}
    candidate_rows = 0
    rejected_samples: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Anbaugebiet:"):
            anbaugebiet = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("Bereich:"):
            bereich = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("Großlage:") or stripped.startswith("Grosslage:"):
            grosslage = stripped.split(":", 1)[1].strip()
            continue
        if not re.match(r"^\s*\d{6}\b", line):
            continue

        candidate_rows += 1
        fields = [field.strip() for field in re.split(r"\s{2,}", stripped) if field.strip()]
        if len(fields) < 5 or not re.fullmatch(r"\d{6}", fields[0]):
            if len(rejected_samples) < 20:
                rejected_samples.append(stripped)
            continue

        code, name, municipality, cadastral, area_text = fields[:5]
        area_match = re.match(r"^(\d+(?:[.,]\d+)?)", area_text)
        if not name or not municipality or not cadastral or area_match is None:
            if len(rejected_samples) < 20:
                rejected_samples.append(stripped)
            continue
        area_ha = float(area_match.group(1).replace(",", "."))
        region = anbaugebiet or "Rheinland-Pfalz"
        parent = grosslage or bereich or region

        records[code] = {
            "id": f"site:germany:rlp:einzellage:{code}",
            "name": name,
            "country": "Germany",
            "region": region,
            "parent": parent,
            "commune": municipality,
            "site_type": "einzellage",
            "classification": "Einzellage",
            "legal_status": "official_weinbergsrolle_snapshot_2024",
            "area_ha": area_ha,
            "source_ids": ["rlp_weinlagen_register_2024"],
            "effective_from": "2024",
            "notes": (
                f"Landwirtschaftskammer Rheinland-Pfalz Weinlagen register, Ernte 2024; "
                f"Lagennummer {code}; Gemarkung {cadastral}; planted vineyard area {area_ha:g} ha."
            ),
        }

    if len(records) < 1500:
        raise ValueError(
            f"RLP PDF parser produced only {len(records)} records from {candidate_rows} six-digit candidates; "
            f"rejected samples={rejected_samples[:8]}"
        )
    return sorted(records.values(), key=lambda row: (row["region"], row.get("parent") or "", row["commune"], row["name"].casefold()))


def _write(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    checked = datetime.now(timezone.utc).date().isoformat()

    noe_features = _features(NOE_WFS_URL, "OGD:RLF_WEINBAU_RIEDEN")
    noe_records = _noe_records(noe_features)
    _write(NOE_OUT, {
        "schema_version": "2.0",
        "generated": checked,
        "notes": (
            "Machine-materialized current Land Niederösterreich Rieden dataset. "
            "The publisher states statewide capture is not yet complete; absence is not evidence that a Ried does not exist."
        ),
        "sources": {
            "noe_rieden_wfs_2026": {
                "authority": "Land Niederösterreich, Abteilung BD1 - GIS Support",
                "url": NOE_SOURCE_PAGE,
                "data_url": NOE_WFS_URL,
                "checked": checked,
                "scope": "Current official Weinbaurieden/Subrieden OGD WFS identity and geometry.",
                "evidence_class": "official_state_vineyard_registry_wfs",
                "license": "Creative Commons Namensnennung 4.0 International",
            }
        },
        "groups": [],
        "records": noe_records,
    })

    rlp_pdf = _download(RLP_PDF_URL, accept="application/pdf")
    rlp_records = _rlp_records_from_pdf(rlp_pdf)
    _write(RLP_OUT, {
        "schema_version": "2.0",
        "generated": checked,
        "notes": (
            "Machine-materialized official Rheinland-Pfalz Weinlagen register snapshot for Ernte 2024. "
            "This is authoritative historical registry evidence; it is not silently treated as a live 2026 legal snapshot."
        ),
        "sources": {
            "rlp_weinlagen_register_2024": {
                "authority": "Landwirtschaftskammer Rheinland-Pfalz",
                "url": RLP_SOURCE_PAGE,
                "data_url": RLP_PDF_URL,
                "checked": checked,
                "source_effective_label": "Ernte 2024",
                "scope": "Official Einzellage register rows with Lagennummer, municipality, cadastral district and planted area.",
                "evidence_class": "official_vineyard_register_snapshot_pdf",
            }
        },
        "groups": [],
        "records": rlp_records,
    })

    manifest = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "noe_wfs_features": len(noe_features),
        "noe_sites_materialized": len(noe_records),
        "rlp_einzellagen_materialized": len(rlp_records),
        "rlp_status": "official_2024_register_snapshot_materialized",
        "outputs": [str(NOE_OUT.relative_to(ROOT)), str(RLP_OUT.relative_to(ROOT))],
    }
    _write(MANIFEST_OUT, manifest)
    print("VINEYARD_DACH_SYNC=" + json.dumps(manifest, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
