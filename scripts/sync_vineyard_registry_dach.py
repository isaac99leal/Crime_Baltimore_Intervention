#!/usr/bin/env python3
"""Materialize official German/Austrian named-vineyard registries.

The sync is jurisdiction-independent: one unavailable public endpoint never
blocks a second authoritative registry. A failed jurisdiction is recorded in
the manifest and remains unmaterialized rather than being guessed.

Current live source:
- Land Niederösterreich OGD WFS (Rieden/Subrieden)

Rheinland-Pfalz remains wired as an optional WFS source, but its historical
GeoServer endpoint was returning 404 on 2026-09-05. The official LWK register
therefore remains a researched source until a stable current machine endpoint
or the official register PDF parser is promoted.
"""
from __future__ import annotations

import json
import re
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
RLP_WFS_URLS = (
    "https://weinlagen.lwk-rlp.de/geoserver/lwk/ows",
    "http://weinlagen.lwk-rlp.de/geoserver/lwk/ows",
)
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


def _request_json(base_url: str, params: Mapping[str, str], attempts: int = 4) -> dict[str, Any]:
    url = base_url + ("&" if "?" in base_url else "?") + urllib.parse.urlencode(params)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
            doc = json.loads(payload)
            if not isinstance(doc, dict):
                raise ValueError("Expected JSON object")
            return doc
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Could not fetch {url}: {last_error}")


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


def _optional_rlp() -> tuple[list[dict[str, Any]], str | None, str | None]:
    errors: list[str] = []
    for endpoint in RLP_WFS_URLS:
        try:
            features = _features(endpoint, "lwk:Weinlagen", "1.1.0")
            if features:
                keys = sorted(_properties(features[0]))
                return [], endpoint, "Endpoint responded, but RLP schema promotion is intentionally pending: " + ",".join(keys)
        except Exception as exc:
            errors.append(f"{endpoint}: {exc}")
    return [], None, " | ".join(errors)


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

    rlp_records, rlp_endpoint, rlp_error = _optional_rlp()
    if rlp_records:
        _write(RLP_OUT, {
            "schema_version": "2.0", "generated": checked,
            "sources": {"rlp_weinbergsrolle_wfs_2026": {"authority": "Landwirtschaftskammer Rheinland-Pfalz", "url": RLP_SOURCE_PAGE, "data_url": rlp_endpoint, "checked": checked}},
            "groups": [], "records": rlp_records,
        })

    manifest = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "noe_wfs_features": len(noe_features),
        "noe_sites_materialized": len(noe_records),
        "rlp_einzellagen_materialized": len(rlp_records),
        "rlp_status": "materialized" if rlp_records else "official_source_unavailable_or_schema_pending",
        "rlp_error": rlp_error,
        "outputs": [str(NOE_OUT.relative_to(ROOT))] + ([str(RLP_OUT.relative_to(ROOT))] if rlp_records else []),
    }
    _write(MANIFEST_OUT, manifest)
    print("VINEYARD_DACH_SYNC=" + json.dumps(manifest, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
