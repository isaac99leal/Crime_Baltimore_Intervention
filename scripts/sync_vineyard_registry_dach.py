#!/usr/bin/env python3
"""Materialize official German/Austrian named-vineyard registries.

This synchronizer deliberately stores legal/site identity and provenance only.
It does not infer grape permissions, soils, ownership, slope, elevation, or
other terroir attributes from regional context.

Sources:
- Landwirtschaftskammer Rheinland-Pfalz Weinlagen WFS (Einzellagen)
- Land Niederösterreich OGD WFS (Rieden/Subrieden)
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
from typing import Any, Iterable, Mapping

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
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "unknown"


def _norm_key(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]", "",
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold(),
    )


def _request_json(base_url: str, params: Mapping[str, str], *, attempts: int = 4) -> dict[str, Any]:
    url = base_url + ("&" if "?" in base_url else "?") + urllib.parse.urlencode(params)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as response:
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


def _feature_collection(base_url: str, *, type_name: str, version: str = "2.0.0") -> list[dict[str, Any]]:
    type_key = "typeName" if version.startswith("1.") else "typeNames"
    params = {
        "service": "WFS",
        "version": version,
        "request": "GetFeature",
        type_key: type_name,
        "count": "10000",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
    }
    doc = _request_json(base_url, params)
    features = doc.get("features")
    if not isinstance(features, list):
        raise ValueError(f"{type_name}: WFS response has no feature list; keys={sorted(doc)}")
    return [f for f in features if isinstance(f, dict)]


def _props(feature: Mapping[str, Any]) -> dict[str, Any]:
    raw = feature.get("properties", {})
    return dict(raw) if isinstance(raw, Mapping) else {}


def _pick(props: Mapping[str, Any], exact: Iterable[str], contains: Iterable[str] = ()) -> Any:
    index = {_norm_key(k): v for k, v in props.items()}
    for key in exact:
        value = index.get(_norm_key(key))
        if value not in (None, ""):
            return value
    contains_norm = tuple(_norm_key(v) for v in contains)
    for key, value in index.items():
        if value in (None, ""):
            continue
        if any(part and part in key for part in contains_norm):
            return value
    return None


def _text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def _number_text(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    return digits or None


def _date_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _rlp_fetch() -> tuple[list[dict[str, Any]], str]:
    errors: list[str] = []
    for endpoint in RLP_WFS_URLS:
        try:
            return _feature_collection(endpoint, type_name="lwk:Weinlagen", version="1.1.0"), endpoint
        except Exception as exc:
            errors.append(f"{endpoint}: {exc}")
    raise RuntimeError("RLP WFS unavailable: " + " | ".join(errors))


def _rlp_name(props: Mapping[str, Any]) -> str | None:
    return _text(_pick(
        props,
        (
            "einzellage", "weinlage", "lagename", "lage_name", "lagenbez",
            "lagebezeichnung", "bezeichnung", "name", "nam",
        ),
        ("einzellage", "lagename", "weinlage"),
    ))


def _rlp_code(props: Mapping[str, Any]) -> str | None:
    value = _pick(
        props,
        ("weinlagennummer", "weinlagenr", "lagennummer", "lagenr", "bezeichner", "bez"),
        ("lagennummer", "weinlagenr"),
    )
    digits = _number_text(value)
    return digits if digits and len(digits) >= 5 else None


def _rlp_region(props: Mapping[str, Any]) -> str | None:
    return _text(_pick(props, ("anbaugebiet", "weinbaugebiet", "gebiet"), ("anbaugebiet",)))


def _rlp_records(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not features:
        raise ValueError("RLP WFS returned zero features")
    first_keys = sorted(_props(features[0]))
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    unresolved = 0

    for feature in features:
        props = _props(feature)
        name = _rlp_name(props)
        code = _rlp_code(props)
        if not name:
            unresolved += 1
            continue

        region = _rlp_region(props) or "Rheinland-Pfalz"
        commune = _text(_pick(props, ("gemeinde", "leitgemeinde", "ort"), ("gemeinde",)))
        gemarkung = _text(_pick(props, ("gemarkung", "gemarkungsname"), ("gemarkung",)))
        parent = commune or gemarkung or region
        identity = (code or "", name.casefold())
        site_id = (
            f"site:germany:rlp:einzellage:{code}"
            if code
            else f"site:germany:rlp:{_slug(parent)}:einzellage:{_slug(name)}"
        )

        row = rows.get(identity)
        if row is None:
            row = {
                "id": site_id,
                "name": name,
                "country": "Germany",
                "region": region,
                "parent": parent,
                "commune": commune or gemarkung,
                "site_type": "einzellage",
                "classification": "Einzellage",
                "legal_status": "official_weinbergsrolle_einzellage",
                "source_ids": ["rlp_weinbergsrolle_wfs_2026"],
                "geometry_source_id": "rlp_weinbergsrolle_wfs_2026",
                "notes": f"Official Weinbergsrolle WFS identity{f'; Weinlagennummer {code}' if code else ''}.",
            }
            rows[identity] = row
        else:
            cadastral = [v for v in (commune, gemarkung) if v]
            if cadastral:
                additions = ", ".join(sorted(set(cadastral)))
                marker = f" Additional source locality: {additions}."
                if marker not in row["notes"]:
                    row["notes"] += marker

    if not rows:
        raise ValueError(
            "RLP WFS schema could not be mapped to Einzellage names. "
            f"First feature property keys: {first_keys}"
        )
    if unresolved > max(20, len(features) // 10):
        raise ValueError(
            f"RLP WFS left {unresolved}/{len(features)} features without a legal site name; "
            f"first keys={first_keys}"
        )

    return sorted(rows.values(), key=lambda r: (r["region"], r.get("parent") or "", r["name"].casefold()))


def _noe_records(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not features:
        raise ValueError("Niederösterreich WFS returned zero features")
    rows: dict[str, dict[str, Any]] = {}

    for feature in features:
        props = _props(feature)
        ried = _text(props.get("WEINBAURIEDE1"))
        subried = _text(props.get("WEINBAURIEDE2"))
        flur = _text(props.get("WEINBAUFLUR"))
        kg = _text(props.get("KGNAME"))
        municipality = _text(props.get("PGNAME"))
        status = _text(props.get("UMSETZUNG_STATUS"))
        last_update = _text(props.get("LASTUPDATE"))
        if not ried:
            continue

        parent = flur or kg or municipality or "Niederösterreich"
        main_id = (
            f"site:austria:niederoesterreich:{_slug(kg or municipality or parent)}:"
            f"ried:{_slug(ried)}"
        )
        rows.setdefault(
            main_id,
            {
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
                "notes": (
                    f"Land Niederösterreich OGD record; status={status or 'unknown'}"
                    f"{'; source last update ' + last_update if last_update else ''}."
                ),
            },
        )

        if subried and subried.casefold() not in {"keine subriede", "keine subried", "none", "-"}:
            sub_id = f"{main_id}:subried:{_slug(subried)}"
            rows.setdefault(
                sub_id,
                {
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
                    "notes": (
                        f"Land Niederösterreich OGD record; status={status or 'unknown'}"
                        f"{'; source last update ' + last_update if last_update else ''}."
                    ),
                },
            )

    if not rows:
        first_keys = sorted(_props(features[0]))
        raise ValueError(f"Niederösterreich WFS schema yielded no Rieden; first keys={first_keys}")
    return sorted(rows.values(), key=lambda r: (r.get("commune") or "", r["site_type"], r["name"].casefold()))


def _document(*, source_id: str, source: dict[str, Any], records: list[dict[str, Any]], notes: str) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "generated": _date_iso(),
        "notes": notes,
        "sources": {source_id: source},
        "groups": [],
        "records": records,
    }


def _write(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    rlp_features, rlp_endpoint = _rlp_fetch()
    rlp_records = _rlp_records(rlp_features)
    noe_features = _feature_collection(NOE_WFS_URL, type_name="OGD:RLF_WEINBAU_RIEDEN")
    noe_records = _noe_records(noe_features)

    checked = _date_iso()
    _write(
        RLP_OUT,
        _document(
            source_id="rlp_weinbergsrolle_wfs_2026",
            source={
                "authority": "Landwirtschaftskammer Rheinland-Pfalz",
                "url": RLP_SOURCE_PAGE,
                "data_url": rlp_endpoint,
                "checked": checked,
                "scope": "Official Weinbergsrolle/Weinlagen WFS identity for Rheinland-Pfalz Einzellagen.",
                "evidence_class": "official_state_vineyard_register_wfs",
                "license": "Datenlizenz Deutschland – Namensnennung – Version 2.0",
            },
            records=rlp_records,
            notes=(
                "Machine-materialized official Rheinland-Pfalz Einzellage identities. "
                "The source itself warns that cross-municipality sites are subject to Leitgemeinde rules; "
                "this file does not infer legal label wording beyond site identity."
            ),
        ),
    )
    _write(
        NOE_OUT,
        _document(
            source_id="noe_rieden_wfs_2026",
            source={
                "authority": "Land Niederösterreich, Abteilung BD1 - GIS Support",
                "url": NOE_SOURCE_PAGE,
                "data_url": NOE_WFS_URL,
                "checked": checked,
                "scope": "Official currently materialized/verordnete Weinbaurieden and Subrieden in the Niederösterreich OGD WFS.",
                "evidence_class": "official_state_vineyard_registry_wfs",
                "license": "Creative Commons Namensnennung 4.0 International",
            },
            records=noe_records,
            notes=(
                "Machine-materialized current Land Niederösterreich Rieden dataset. "
                "The publisher explicitly states that statewide capture is not yet complete; "
                "absence from this snapshot is therefore not evidence that a Ried does not exist."
            ),
        ),
    )

    manifest = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "rlp_wfs_features": len(rlp_features),
        "rlp_einzellagen_materialized": len(rlp_records),
        "noe_wfs_features": len(noe_features),
        "noe_sites_materialized": len(noe_records),
        "outputs": [str(RLP_OUT.relative_to(ROOT)), str(NOE_OUT.relative_to(ROOT))],
    }
    _write(MANIFEST_OUT, manifest)
    print("VINEYARD_DACH_SYNC=" + json.dumps(manifest, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
