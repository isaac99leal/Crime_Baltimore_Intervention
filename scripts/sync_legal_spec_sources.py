#!/usr/bin/env python3
"""Index authoritative legal wine product-specification documents at scale.

The EU eAmbrosia register is the primary discovery spine. This script maps every
registered wine GI to its application record and records the national product-
specification and EU single-document attachment identifiers exposed by the
Commission public API.

Important: an indexed document is evidence that a legal specification exists; it
is NOT itself a machine-readable authorization rule. Strict wine generation is
allowed only after a separate deterministic extractor has promoted the relevant
rule with provenance and confidence metadata.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "sommelier_v2" / "knowledge" / "data"
EAMBROSIA_WINES = DATA / "eambrosia_wine_gis.json"
OUT = DATA / "legal_spec_source_index.json"
MANIFEST = DATA / "legal_spec_source_manifest.json"

PUBLIC_API = "https://ec.europa.eu/geographical-indications-register/eambrosia-public-api"
FILTER_URL = PUBLIC_API + "/api/gi-applications/filter"
DETAIL_URL = PUBLIC_API + "/api/gi-applications/id/{application_id}"
ATTACHMENT_URL = PUBLIC_API + "/api/v1/attachments/{attachment_id}"
USER_AGENT = "SommelierSimulatorLegalSpecSync/1.0 (+public regulatory data indexing)"


def _request_json(url: str, *, payload: dict[str, Any] | None = None, timeout: int = 90) -> Any:
    data = None
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    last: Exception | None = None
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last}")


def _find_application_rows(obj: Any) -> list[dict[str, Any]]:
    """Find the filter response's application rows without binding to one API wrapper shape."""
    if isinstance(obj, list):
        dicts = [x for x in obj if isinstance(x, dict)]
        if dicts and sum(bool(x.get("fileName") or x.get("fileNumber")) for x in dicts) >= max(1, len(dicts) // 4):
            return dicts
        for value in obj:
            found = _find_application_rows(value)
            if found:
                return found
    elif isinstance(obj, dict):
        for key in ("content", "rows", "data", "items", "results", "result"):
            if key in obj:
                found = _find_application_rows(obj[key])
                if found:
                    return found
        for value in obj.values():
            found = _find_application_rows(value)
            if found:
                return found
    return []


def _application_id(row: dict[str, Any]) -> str | None:
    for key in ("id", "applicationId", "applicationID", "appId"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _file_number(row: dict[str, Any]) -> str:
    return str(row.get("fileName") or row.get("fileNumber") or "").strip()


def _collect_attachment_ids(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, dict):
        uri = value.get("uri")
        if uri is not None and str(uri).strip():
            text = str(uri).strip()
            if text.rsplit("/", 1)[-1].isdigit():
                result.append(text.rsplit("/", 1)[-1])
        for child in value.values():
            result.extend(_collect_attachment_ids(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(_collect_attachment_ids(child))
    return result


def _field_ci(doc: dict[str, Any], *names: str) -> Any:
    wanted = {name.casefold() for name in names}
    for key, value in doc.items():
        if key.casefold() in wanted:
            return value
    return None


def _extract_detail_attachments(detail: dict[str, Any]) -> tuple[list[str], list[str]]:
    product_value = _field_ci(
        detail,
        "productSpecifications", "productSpecification", "productSpecificationFile",
        "productSpecTechFile", "productSpecFiles",
    )
    single_value = _field_ci(
        detail,
        "singleDocTechFile", "singleDocument", "singleDocuments", "summarySheets",
        "singleDocumentFile",
    )
    product = sorted(set(_collect_attachment_ids(product_value)))
    single = sorted(set(_collect_attachment_ids(single_value)))

    # API versions have moved these arrays under nested application objects.
    if not product or not single:
        for key, value in detail.items():
            folded = key.casefold()
            if not product and "productspec" in folded:
                product = sorted(set(_collect_attachment_ids(value)))
            if not single and ("singledoc" in folded or "summarysheet" in folded):
                single = sorted(set(_collect_attachment_ids(value)))
    return product, single


def _load_previous() -> dict[str, dict[str, Any]]:
    if not OUT.exists():
        return {}
    try:
        rows = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(rows, list):
        return {}
    return {str(row.get("gi_identifier")): row for row in rows if isinstance(row, dict) and row.get("gi_identifier")}


def _detail_for(application_id: str) -> dict[str, Any]:
    raw = _request_json(DETAIL_URL.format(application_id=application_id))
    if not isinstance(raw, dict):
        raise ValueError(f"Unexpected application detail shape for id={application_id}")
    return raw


def main() -> None:
    if not EAMBROSIA_WINES.exists():
        raise SystemExit("Run scripts/sync_external_knowledge_ci.py first; eambrosia_wine_gis.json is missing")
    wines = json.loads(EAMBROSIA_WINES.read_text(encoding="utf-8"))
    if not isinstance(wines, list):
        raise SystemExit("Unexpected eambrosia_wine_gis.json shape")

    filtered = _request_json(FILTER_URL, payload={"first": 0, "rows": 5000, "showTSGs": "false", "filters": []}, timeout=180)
    app_rows = _find_application_rows(filtered)
    if len(app_rows) < 1000:
        raise RuntimeError(f"eAmbrosia application filter returned only {len(app_rows)} usable rows")
    by_file = {_file_number(row): row for row in app_rows if _file_number(row)}

    previous = _load_previous()
    targets: list[tuple[dict[str, Any], str]] = []
    output: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for wine in wines:
        if not isinstance(wine, dict) or wine.get("removed") or wine.get("status") != "registered":
            continue
        gi = str(wine.get("gi_identifier") or "")
        file_number = str(wine.get("file_number") or "")
        app = by_file.get(file_number)
        application_id = _application_id(app or {})
        base = {
            "gi_identifier": gi,
            "file_number": file_number,
            "protected_names": wine.get("protected_names") or [],
            "countries": wine.get("countries") or [],
            "gi_type": wine.get("gi_type"),
            "status": wine.get("status"),
            "modification_date": wine.get("modification_date"),
            "application_id": application_id,
        }
        old = previous.get(gi)
        if (
            old
            and old.get("modification_date") == base["modification_date"]
            and old.get("application_id") == application_id
            and (old.get("product_specification_attachment_ids") or old.get("single_document_attachment_ids"))
        ):
            output.append(old)
        elif application_id:
            targets.append((base, application_id))
        else:
            base.update({
                "product_specification_attachment_ids": [],
                "single_document_attachment_ids": [],
                "source_urls": [],
                "index_status": "application_id_unresolved",
            })
            output.append(base)

    with ThreadPoolExecutor(max_workers=16) as pool:
        future_map = {pool.submit(_detail_for, app_id): (base, app_id) for base, app_id in targets}
        for future in as_completed(future_map):
            base, app_id = future_map[future]
            try:
                detail = future.result()
                product, single = _extract_detail_attachments(detail)
                source_urls = [ATTACHMENT_URL.format(attachment_id=x) for x in product + single]
                row = dict(base)
                row.update({
                    "product_specification_attachment_ids": product,
                    "single_document_attachment_ids": single,
                    "source_urls": source_urls,
                    "index_status": "product_specification_indexed" if product else "single_document_only" if single else "no_attachment_exposed",
                })
                output.append(row)
            except Exception as exc:
                row = dict(base)
                row.update({
                    "product_specification_attachment_ids": [],
                    "single_document_attachment_ids": [],
                    "source_urls": [],
                    "index_status": "detail_fetch_error",
                })
                output.append(row)
                errors.append({"gi_identifier": str(base["gi_identifier"]), "application_id": app_id, "error": f"{type(exc).__name__}: {exc}"})

    output.sort(key=lambda row: (str(row.get("countries")), str(row.get("protected_names")), str(row.get("gi_identifier"))))
    DATA.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with_product = sum(bool(row.get("product_specification_attachment_ids")) for row in output)
    with_single = sum(bool(row.get("single_document_attachment_ids")) for row in output)
    indexed = sum(row.get("index_status") in {"product_specification_indexed", "single_document_only"} for row in output)
    countries = {country for row in output for country in (row.get("countries") or [])}
    manifest = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "source": FILTER_URL,
        "registered_wine_gis": len(output),
        "countries": len(countries),
        "with_product_specification": with_product,
        "with_single_document": with_single,
        "with_any_authoritative_document": indexed,
        "detail_fetch_errors": len(errors),
        "errors": errors[:50],
        "safety": "Source indexing does not authorize a grape/origin combination. Strict generation requires promoted machine rules.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("LEGAL_SPEC_SOURCE_SYNC=" + json.dumps(manifest, sort_keys=True))

    # Fail on catastrophic source/API regressions, not on isolated unavailable records.
    if len(output) < 1000 or indexed < max(500, int(len(output) * 0.45)):
        raise RuntimeError(f"Legal source coverage is suspiciously low: {indexed}/{len(output)}")


if __name__ == "__main__":
    main()
