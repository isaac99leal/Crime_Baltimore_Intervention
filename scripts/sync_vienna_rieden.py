#!/usr/bin/env python3
"""Materialize all 140 official Vienna Weinbaurieden from the city regulation.

The Magistrat der Stadt Wien regulation entered into force 2016-07-01 and
enumerates vineyard land by district, Katastralgemeinde (KG), Riede, and parcel
numbers. Its fixed-column text contains 145 administrative Riede headings. The
City's official Riedenkarte contains 140 Weinbaurieden because five named sites
continue across KG boundaries.

Those five cross-KG continuations are explicit below. Same-spelling homonyms in
other districts/KGs remain separate. This prevents both over-merging and
under-merging while preserving every legal source occurrence.

The sync records site identity and legal parent context only. It does not infer
parcel geometry, area, ownership, soil, slope, elevation, or permitted grapes.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
import unicodedata
import urllib.request
from collections import defaultdict
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


def _identity(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value.casefold().replace("ß", "ss")).strip()


# The City/Landwirtschaftskammer 2016 parcel maps show these Rieden crossing KG
# boundaries. Five administrative duplicates are consolidated, reconciling the
# regulation's 145 Riede headings with the City's published 140-Rieden total.
#
# Deliberately NOT merged:
# - Mitterberg in Heiligenstadt vs Mitterberg in Neustift/Salmannsdorf
# - Neuberg in Kalksburg vs Neuberg in Neustift/Salmannsdorf
# - Rothen in Heiligenstadt vs Rothen in Stammersdorf
# - Sätzen in Stammersdorf vs Sätzen in Liesing
CROSS_KG_GROUPS: dict[tuple[str, int, str], str] = {
    ("hungerberg", 19, "grinzing"): "hungerberg-grinzing-unterdobling",
    ("hungerberg", 19, "unterdobling"): "hungerberg-grinzing-unterdobling",
    ("mitterberg", 19, "neustift am walde"): "mitterberg-neustift-salmannsdorf",
    ("mitterberg", 19, "salmannsdorf"): "mitterberg-neustift-salmannsdorf",
    ("neuberg", 19, "neustift am walde"): "neuberg-neustift-salmannsdorf",
    ("neuberg", 19, "salmannsdorf"): "neuberg-neustift-salmannsdorf",
    ("hackenberg", 19, "obersievering"): "hackenberg-sievering",
    ("hackenberg", 19, "untersievering"): "hackenberg-sievering",
    ("reisberg", 23, "kalksburg"): "reisberg-kalksburg-rodaun",
    ("reisberg", 23, "rodaun"): "reisberg-kalksburg-rodaun",
}


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


def _group_token(district: int, kg: str, name: str) -> str:
    name_key = _identity(name)
    kg_key = _identity(kg)
    cross = CROSS_KG_GROUPS.get((name_key, district, kg_key))
    if cross:
        return f"cross:{district}:{cross}"
    return f"local:{district}:{kg_key}:{name_key}"


def _records(payload: bytes) -> tuple[list[dict[str, object]], int, int]:
    text = _pdf_text(payload)
    district: int | None = None
    kg: str | None = None
    occurrences: list[tuple[int, str, str]] = []

    district_re = re.compile(r"(?:im|Im)\s+(\d{1,2})\.\s+Wiener\s+Gemeindebezirk")
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

        name = riede_match.group(1).strip().rstrip(".")
        if district is None or kg is None:
            raise ValueError(f"Riede {name!r} appeared without district/KG context")
        occurrences.append((district, kg, name))

    grouped: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for occurrence in occurrences:
        grouped[_group_token(*occurrence)].append(occurrence)

    if len(occurrences) != 145 or len(grouped) != 140:
        duplicate_groups = {
            key: rows for key, rows in grouped.items() if len(rows) > 1
        }
        raise ValueError(
            f"Vienna parser found {len(occurrences)} administrative Riede headings "
            f"and {len(grouped)} legal site identities; expected 145 and 140; "
            f"duplicate_groups={duplicate_groups}"
        )

    merged_groups = [rows for rows in grouped.values() if len(rows) > 1]
    if len(merged_groups) != 5:
        raise ValueError(f"Expected exactly five cross-KG Vienna Rieden, found {len(merged_groups)}")

    records: list[dict[str, object]] = []
    for token, source_rows in grouped.items():
        source_spellings = {name for _, _, name in source_rows}
        if len(source_spellings) != 1:
            raise ValueError(f"Vienna identity {token!r} has conflicting spellings: {sorted(source_spellings)}")
        name = next(iter(source_spellings))
        districts = sorted({district for district, _, _ in source_rows})
        kgs = sorted({kg for _, kg, _ in source_rows})
        if len(districts) != 1:
            raise ValueError(f"Cross-district site merge is forbidden: {token} -> {districts}")
        district_value = districts[0]
        kg_text = "; ".join(kgs)

        if token.startswith("cross:"):
            canonical = token.split(":", 2)[2]
            site_id = f"site:austria:wien:{district_value:02d}:ried:{canonical}"
        else:
            site_id = f"site:austria:wien:{district_value:02d}:{_slug(kgs[0])}:ried:{_slug(name)}"

        records.append({
            "id": site_id,
            "name": name,
            "country": "Austria",
            "region": "Wien",
            "parent": kg_text,
            "commune": kg_text,
            "site_type": "ried",
            "classification": "Ried",
            "legal_status": "official_city_ried_2016",
            "row_count": len(source_rows),
            "source_ids": ["wien_rieden_regulation_2016"],
            "effective_from": "2016-07-01",
            "notes": (
                f"Magistrat der Stadt Wien legal Riedenkarte identity; district {district_value}; "
                f"Katastralgemeinde(n) {kg_text}. Parcel-level delineation is present in the "
                "official source; no geometry is reconstructed in this record."
            ),
        })

    return (
        sorted(records, key=lambda row: (str(row["name"]).casefold(), str(row["commune"]))),
        len(occurrences),
        len(merged_groups),
    )


def _write(path: Path, document: dict[str, object]) -> None:
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    checked = datetime.now(timezone.utc).date().isoformat()
    records, heading_count, cross_kg_count = _records(_download(REGULATION_URL))
    document = {
        "schema_version": "2.0",
        "generated": checked,
        "notes": (
            "All 140 Vienna Weinbaurieden materialized from the official 2016 city regulation. "
            "The regulation contains 145 administrative Riede headings; five cross-KG "
            "continuations are consolidated using the official parcel-map context. Same-name "
            "homonyms outside those five mappings remain separate. No site physical attributes "
            "are inferred here."
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
        "vienna_regulation_ried_headings": heading_count,
        "vienna_cross_kg_rieden": cross_kg_count,
        "source_effective_from": "2016-07-01",
        "output": str(OUT.relative_to(ROOT)),
    }
    _write(MANIFEST, manifest)
    print("VINEYARD_VIENNA_SYNC=" + json.dumps(manifest, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
