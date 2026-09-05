#!/usr/bin/env python3
"""Materialize all 140 official Vienna Weinbaurieden from the city regulation.

The source is the Magistrat der Stadt Wien regulation that entered into force
2016-07-01. It enumerates vineyard land by district, cadastral municipality
(Katastralgemeinde), Riede, and parcel numbers. This sync records site identity
and the legal parent hierarchy only; it does not manufacture parcel geometry or
site-level terroir attributes from the parcel-number lists.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "sommelier_v2" / "knowledge" / "data"
OUT = DATA_DIR / "named_sites_expansion_2026_austria_vienna.json"
MANIFEST = DATA_DIR / "vineyard_registry_vienna_sync_manifest.json"
SOURCE_PAGE = "https://www.wien.gv.at/umwelt/weinbaufluren-riedenkarte"
REGULATION_URL = "https://www.wien.gv.at/pdf/ma22/abgrenzung-weinbaufluren.pdf"
UA = "SommelierSimulatorV2/1.0 (+https://github.com/isaac99leal/Crime_Baltimore_Intervention)"


def _slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold().replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "unknown"


def _download(url: str, attempts: int = 4) -> bytes:
    error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf"})
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except Exception as exc:
            error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Could not fetch {url}: {error}")


def _pdf_text(payload: bytes) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "vienna-rieden.pdf"
        path.write_bytes(payload)
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pdftotext failed: {result.stderr.strip()}")
        return result.stdout


def _records(payload: bytes) -> list[dict[str, object]]:
    text = _pdf_text(payload)
    district: int | None = None
    kg: str | None = None
    rows: dict[str, dict[str, object]] = {}
    riede_occurrences = 0

    district_re = re.compile(r"(?:im|Im)\s+(\d{1,2})\.\s+Wiener\s+Gemeindebezirk")
    # Most district sections use lettered sub-headings such as
    # "a) in der KG Schönbrunn:". The optional prefix is part of the source
    # layout, not the cadastral name, and must not cause KG context to leak.
    kg_re = re.compile(r"^\s*(?:[a-z]\)\s*)?in\s+der\s+KG\s+(.+?):\s*$", re.IGNORECASE)
    riede_re = re.compile(r"^\s*Riede\s+(.+?)\s*$", re.IGNORECASE)

    for line in text.splitlines():
        district_match = district_re.search(line)
        if district_match:
            district = int(district_match.group(1))
            continue
        kg_match = kg_re.match(line)
        if kg_match:
            kg = kg_match.group(1).strip()
            continue
        riede_match = riede_re.match(line)
        if not riede_match:
            continue

        riede_occurrences += 1
        name = riede_match.group(1).strip().rstrip(".")
        if district is None or kg is None:
            raise ValueError(f"Riede {name!r} appeared without district/KG context")
        site_id = f"site:austria:wien:{district:02d}:{_slug(kg)}:ried:{_slug(name)}"
        row = {
            "id": site_id,
            "name": name,
            "country": "Austria",
            "region": "Wien",
            "parent": kg,
            "commune": kg,
            "site_type": "ried",
            "classification": "Ried",
            "legal_status": "official_city_ried_2016",
            "source_ids": ["wien_rieden_regulation_2016"],
            "effective_from": "2016-07-01",
            "notes": (
                f"Magistrat der Stadt Wien legal Riedenkarte identity; district {district}; "
                f"Katastralgemeinde {kg}. Parcel-level delineation is present in the source regulation."
            ),
        }
        existing = rows.get(site_id)
        if existing is not None and existing != row:
            raise ValueError(f"Conflicting Vienna Ried identity: {site_id}")
        rows[site_id] = row

    # The city states that the official Riedenkarte contains all 140 Rieden.
    # Enforce this as a hard extraction invariant so PDF layout changes cannot
    # silently create a partial legal-site snapshot.
    if len(rows) != 140:
        sample = [row["name"] for row in list(rows.values())[:20]]
        raise ValueError(
            f"Vienna regulation parser found {len(rows)} unique Rieden from "
            f"{riede_occurrences} Riede occurrences; expected exactly 140; sample={sample}"
        )
    return sorted(rows.values(), key=lambda row: (int(str(row["id"]).split(":")[3]), str(row["commune"]), str(row["name"]).casefold()))


def _write(path: Path, document: dict[str, object]) -> None:
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    checked = datetime.now(timezone.utc).date().isoformat()
    records = _records(_download(REGULATION_URL))
    document = {
        "schema_version": "2.0",
        "generated": checked,
        "notes": (
            "All 140 Vienna Weinbaurieden materialized from the official 2016 city regulation. "
            "Names and district/Katastralgemeinde hierarchy are legal-source facts; parcel geometry is not reconstructed here."
        ),
        "sources": {
            "wien_rieden_regulation_2016": {
                "authority": "Magistrat der Stadt Wien / Stadt Wien Umweltschutz",
                "url": SOURCE_PAGE,
                "data_url": REGULATION_URL,
                "checked": checked,
                "effective_from": "2016-07-01",
                "scope": "Official parcel-level delimitation and names of all 140 Vienna Weinbaurieden.",
                "evidence_class": "official_city_vineyard_regulation",
            }
        },
        "groups": [],
        "records": records,
    }
    _write(OUT, document)
    manifest = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "vienna_rieden_materialized": len(records),
        "source_effective_from": "2016-07-01",
        "output": str(OUT.relative_to(ROOT)),
    }
    _write(MANIFEST, manifest)
    print("VINEYARD_VIENNA_SYNC=" + json.dumps(manifest, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
