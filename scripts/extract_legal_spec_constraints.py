#!/usr/bin/env python3
"""Extract deny-safe grape constraints from authoritative product specs.

This is intentionally conservative. A machine-extracted rule may be used to
REJECT a grape that is outside a clearly bounded explicit variety section. It
must never, by itself, authorize a protected-origin wine because composition,
style, process, vintage, and release rules may exist elsewhere in the document.

The first parser tranche covers the largest currently indexed European wine
corpora: France, Italy, Spain, Portugal, Austria, Slovenia, Germany, Greece and
Hungary. Unclear/open-ended variety sections remain source-only.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "sommelier_v2" / "knowledge" / "data"
SOURCE_INDEX = DATA / "legal_spec_source_index.json"
OUT = DATA / "legal_spec_machine_constraints.json"
MANIFEST = DATA / "legal_spec_machine_constraints_manifest.json"
ATTACHMENT_URL = "https://ec.europa.eu/geographical-indications-register/eambrosia-public-api/api/v1/attachments/{attachment_id}"
USER_AGENT = "SommelierSimulatorLegalConstraintExtractor/1.0 (+public regulatory data)"

COUNTRIES = {"FR", "IT", "ES", "PT", "AT", "SI", "DE", "GR", "HU"}

# Start/end patterns locate the legal variety/ampelographic section only. The
# parser does not scan the full document because historical narrative can name
# grapes that are not currently authorized.
SECTION_RULES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "FR": ((r"\benc[ée]pagement\b", r"\bc[ée]pages?\s+autoris[ée]s?\b"),
           (r"\bconduite\s+du\s+vignoble\b", r"\brendements?\b", r"\bVI\s*[.\-–—]")),
    "IT": ((r"\bbase\s+ampelografica\b", r"\bvitigni\s+ammessi\b", r"\bvariet[àa]\s+di\s+vite\b"),
           (r"\bart(?:icolo|\.)\s*3\b", r"\bArt\.\s*3\b")),
    "ES": ((r"\bvariedad(?:es)?\s+de\s+uva\s+de\s+vinificaci[oó]n\b", r"\bvariedades?\s+de\s+vid\b", r"\bvariedades?\s+autorizadas?\b"),
           (r"\brendimientos?\s+m[aá]xim", r"\bpr[aá]cticas?\s+enol[oó]gicas?\b", r"\bzona\s+geogr[aá]fica\b")),
    "PT": ((r"\bcastas?\s+(?:a\s+utilizar|autorizadas?|aptas?)\b", r"\bvariedades?\s+de\s+videira\b", r"\bcastas?\b"),
           (r"\brendimento\b", r"\bpr[aá]ticas?\s+vit[ií]colas?\b", r"\bpr[aá]ticas?\s+enol[oó]gicas?\b")),
    "AT": ((r"\brebsorten\b", r"\brebsortenspektrum\b"),
           (r"\bhektarh[oö]chstertrag\b", r"\bweinbereitung\b", r"\bgeografisches\s+gebiet\b")),
    "SI": ((r"\bsorte\s+vinske\s+trte\b", r"\bsortiment\b", r"\bsorte\b"),
           (r"\bhektarski\s+pridelek\b", r"\bvinogradni[šs]ke\b", r"\bgeografsko\s+obmo[čc]je\b")),
    "DE": ((r"\brebsorten\b", r"\brebsortenspektrum\b"),
           (r"\bhektarh[oö]chstertrag\b", r"\bweinbereitung\b", r"\babgrenzung\s+des\s+gebiet")),
    "GR": ((r"ποικιλ(?:ία|ιες)\s+αμπ[eέ]λου", r"οινοποιήσιμ(?:η|ες)\s+ποικιλ"),
           (r"μ[eέ]γιστη\s+απ[oό]δοση", r"οινολογικ", r"γεωγραφικ")),
    "HU": ((r"\bsz[oő]l[őo]fajt[aá]k\b", r"\benged[eé]lyezett\s+fajt[aá]k\b"),
           (r"\bmaxim[aá]lis\s+hozam\b", r"\bbor[aá]szati\b", r"\bf[oö]ldrajzi\s+ter[uü]let\b")),
}

OPEN_ENDED: dict[str, tuple[str, ...]] = {
    "FR": ("autres cépages", "autres varietes", "variétés de vigne classées", "liste des variétés classées"),
    "IT": ("altre varietà", "altre varieta", "idonee alla coltivazione", "registro nazionale", "raccomandate e/o autorizzate"),
    "ES": ("otras variedades", "registro de variedades", "variedades recomendadas o autorizadas"),
    "PT": ("outras castas", "lista nacional", "outras variedades"),
    "AT": ("alle qualitätsweinrebsorten", "gemäß weingesetz", "gemaess weingesetz"),
    "DE": ("alle qualitätsweinrebsorten", "gemäß weingesetz", "gemaess weingesetz"),
    "SI": ("druge sorte", "vse dovoljene sorte"),
    "GR": ("άλλες ποικιλίες", "αλλες ποικιλιες"),
    "HU": ("egyéb fajták", "egyeb fajtak"),
}


def _request_bytes(url: str, timeout: int = 90) -> bytes:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    last: Exception | None = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last = exc
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"Failed to download {url}: {last}")


def _ascii_norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _load_grape_aliases() -> tuple[re.Pattern[str], dict[str, str]]:
    from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog

    catalog = WorldWineKnowledgeCatalog()
    aliases: dict[str, set[str]] = {}
    for grape in catalog.grapes:
        canonical = str(grape.name)
        for name in (grape.name, *getattr(grape, "aliases", ())):
            key = _ascii_norm(str(name))
            if len(key) >= 4 and not key.isdigit():
                aliases.setdefault(key, set()).add(canonical)
    unambiguous = {key: next(iter(values)) for key, values in aliases.items() if len(values) == 1}
    alternatives = sorted(unambiguous, key=len, reverse=True)
    pattern = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(x) for x in alternatives) + r")(?![a-z0-9])")
    return pattern, unambiguous


def _pdf_text(payload: bytes) -> str:
    if not payload.startswith(b"%PDF"):
        raise ValueError("attachment is not a PDF")
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "spec.pdf"
        pdf.write_bytes(payload)
        result = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), "-"],
            check=True, capture_output=True, text=True, encoding="utf-8",
        )
        return result.stdout


def _section(text: str, country: str) -> tuple[str, str]:
    rules = SECTION_RULES.get(country)
    if rules is None:
        return "", "unsupported_country"
    starts, ends = rules
    start_match = None
    for pattern in starts:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and (start_match is None or match.start() < start_match.start()):
            start_match = match
    if start_match is None:
        return "", "section_not_found"
    start = start_match.start()
    # Variety sections are normally compact. Limit the search window to prevent
    # accidental matches in historical/geographical narrative later in the spec.
    window = text[start:start + 24000]
    end_positions: list[int] = []
    for pattern in ends:
        match = re.search(pattern, window[120:], re.IGNORECASE)
        if match:
            end_positions.append(120 + match.start())
    end = min(end_positions) if end_positions else min(len(window), 12000)
    section = window[:end]
    if len(section.strip()) < 40:
        return "", "section_too_short"
    return section, "section_found"


def _extract_one(row: dict[str, Any], grape_pattern: re.Pattern[str], alias_map: dict[str, str]) -> dict[str, Any]:
    country_list = [str(x) for x in row.get("countries", [])]
    country = next((x for x in country_list if x in COUNTRIES), "")
    base = {
        "gi_identifier": row.get("gi_identifier"),
        "file_number": row.get("file_number"),
        "protected_names": row.get("protected_names") or [],
        "countries": country_list,
        "gi_type": row.get("gi_type"),
        "country_parser": country,
        "source_attachment_id": None,
        "source_url": None,
        "allowed_grapes": [],
        "constraint_level": "source_only",
        "extraction_status": "not_attempted",
        "section_sha256": None,
    }
    attachments = [str(x) for x in row.get("product_specification_attachment_ids", [])]
    if not country or not attachments:
        base["extraction_status"] = "unsupported_country_or_missing_product_spec"
        return base

    attachment = attachments[0]
    url = ATTACHMENT_URL.format(attachment_id=attachment)
    base["source_attachment_id"] = attachment
    base["source_url"] = url
    try:
        payload = _request_bytes(url)
        text = _pdf_text(payload)
        section, status = _section(text, country)
        base["extraction_status"] = status
        if not section:
            return base
        base["section_sha256"] = hashlib.sha256(section.encode("utf-8")).hexdigest()
        normalized = _ascii_norm(section)
        found: list[str] = []
        for match in grape_pattern.finditer(normalized):
            canonical = alias_map.get(match.group(1))
            if canonical and canonical not in found:
                found.append(canonical)
        found.sort(key=str.casefold)
        base["allowed_grapes"] = found

        lowered = section.casefold()
        open_ended = any(marker.casefold() in lowered for marker in OPEN_ENDED.get(country, ()))
        if open_ended:
            base["extraction_status"] = "open_ended_variety_reference"
        elif not found:
            base["extraction_status"] = "section_found_no_known_grape"
        elif len(found) > 80:
            base["extraction_status"] = "implausibly_large_variety_set"
        else:
            # Deny-safe only. This list can reject outsiders but cannot authorize
            # insiders until blend/process completeness is separately verified.
            base["constraint_level"] = "deny_only"
            base["extraction_status"] = "explicit_variety_section_extracted"
    except Exception as exc:
        base["extraction_status"] = "parse_error"
        base["error"] = f"{type(exc).__name__}: {exc}"
    return base


def main() -> None:
    if not SOURCE_INDEX.exists():
        raise SystemExit("legal_spec_source_index.json is missing; run sync_legal_spec_sources.py first")
    source = json.loads(SOURCE_INDEX.read_text(encoding="utf-8"))
    if not isinstance(source, list):
        raise SystemExit("Unexpected legal source index shape")
    grape_pattern, alias_map = _load_grape_aliases()
    targets = [row for row in source if isinstance(row, dict) and any(str(c) in COUNTRIES for c in row.get("countries", []))]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(_extract_one, row, grape_pattern, alias_map): row for row in targets}
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda row: (str(row.get("countries")), str(row.get("protected_names")), str(row.get("gi_identifier"))))
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    deny = [row for row in results if row.get("constraint_level") == "deny_only"]
    country_counts: dict[str, int] = {}
    for row in deny:
        country = str(row.get("country_parser") or "")
        country_counts[country] = country_counts.get(country, 0) + 1
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_records": len(targets),
        "deny_safe_constraints": len(deny),
        "countries_with_deny_safe_constraints": country_counts,
        "source_only_or_unparsed": len(results) - len(deny),
        "safety": "Machine-extracted constraints are deny-only. They never authorize a protected-origin wine.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("LEGAL_MACHINE_CONSTRAINTS=" + json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
