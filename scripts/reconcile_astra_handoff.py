#!/usr/bin/env python3
"""Reproduce handoff coverage and identity queues without changing legal facts."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sommelier_v2.knowledge.catalog import normalize_name
from sommelier_v2.knowledge.legal_specs import LegalSpecRegistry
from sommelier_v2.knowledge.site_claims import SiteClaimRegistry
from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry
from sommelier_v2.knowledge.vineyard_registry import WorldWineKnowledgeCatalog

HANDOFF = ROOT / "docs/astra_handoff/2026-09-06/data"
DATA = ROOT / "sommelier_v2/knowledge/data"


def site_mapping(catalog, claims, parent, name, classification=None):
    scoped = [s for s in catalog.named_sites if s.country == "France"
              and normalize_name(s.parent or "") == normalize_name(parent)
              and (classification is None or normalize_name(s.classification or "") == normalize_name(classification))]
    exact = [s for s in scoped if s.name == name]
    candidates = exact or [s for s in scoped if normalize_name(s.name) == normalize_name(name)]
    bindings = []
    for site in candidates:
        for rule in claims.rules:
            if (normalize_name(rule.parent_appellation) == normalize_name(parent)
                    and rule.country == site.country and rule.site_type == site.site_type
                    and rule.required_site_legal_status == site.legal_status
                    and (not rule.required_site_source_ids or set(rule.required_site_source_ids) & set(site.source_ids))
                    and (not rule.allowed_site_names or site.name in rule.allowed_site_names)
                    and site.name not in rule.excluded_site_names):
                bindings.append({"site_id": site.id, "rule_id": rule.id,
                                 "allowed_wine_variants": rule.allowed_wine_variants})
    bound_ids = {b["site_id"] for b in bindings}
    if not candidates:
        status = "missing_exact_and_normalized_candidate"
    elif not exact:
        status = "spelling_review_required"
    elif len(exact) > 1:
        status = "duplicate_site_records_one_claim_binding" if len(bound_ids) == 1 else "duplicate_site_records_review_required"
    elif not bindings:
        status = "exact_site_without_claim_binding"
    else:
        status = "exact_site_with_claim_binding"
    return {"parent": parent, "source_name": name, "status": status,
            "candidate_sites": [{"id": s.id, "name": s.name, "source_ids": s.source_ids,
                                 "legal_status": s.legal_status} for s in candidates],
            "structural_claim_bindings": bindings,
            "legal_approval": None}


def build_reports(batch_size=250):
    catalog, claims, specs = WorldWineKnowledgeCatalog(), SiteClaimRegistry(), LegalSpecRegistry()
    resolver = VarietyIdentityRegistry()
    pc = []
    parents = set()
    for path in sorted(HANDOFF.glob("ASTRA_BURGUNDY_PC_RECONCILIATION_PART_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for parent, names in doc.get("parents", {}).items():
            parents.add(parent)
            for name in names:
                pc.append(dict(site_mapping(catalog, claims, parent, name, "Premier Cru"), handoff_file=path.name))
    gc_path = HANDOFF / "ASTRA_BURGUNDY_GC_AOCS_RECONCILIATION.json"
    gc = []
    for row in json.loads(gc_path.read_text())["grand_cru_aocs"]:
        matched = [s for s in specs.specs if s.country == "France" and s.appellation == row[1]]
        alias_matches = [s for s in specs.specs if s.country == "France" and row[1] in s.aliases]
        folded_matches = [s for s in specs.specs if s.country == "France"
                          and normalize_name(s.appellation) == normalize_name(row[1])]
        status = ("strict_spec_present" if matched else "explicit_spec_alias_present" if alias_matches
                  else "spec_spelling_review_required" if folded_matches else "strict_spec_missing")
        matched = matched or alias_matches or folded_matches
        gc.append({"handoff_id": row[0], "source_name": row[1],
                   "status": status, "canonical_names": sorted({s.appellation for s in matched}),
                   "strict_spec_ids": [s.id for s in matched], "legal_approval": None})
    suffix_path = HANDOFF / "ASTRA_BURGUNDY_GC_SUBDENOMS_RECONCILIATION.json"
    suffix = [dict(site_mapping(catalog, claims, r[1], r[2]), handoff_id=r[0])
              for r in json.loads(suffix_path.read_text())["grand_cru_label_subdenominations"]]
    burgundy = {
        "schema_version": "1.0", "scope": "Structural reconciliation, not legal validation or new authority",
        "legal_approval_policy": "A source-name match does not validate color, blend, vintage, process, or release.",
        "summary": {"pc_source_rows": len(pc), "pc_parents": len(parents),
                    "pc_status_counts": dict(Counter(r["status"] for r in pc)),
                    "gc_aoc_rows": len(gc), "gc_status_counts": dict(Counter(r["status"] for r in gc)),
                    "gc_suffix_rows": len(suffix), "gc_suffix_status_counts": dict(Counter(r["status"] for r in suffix))},
        "premier_cru": pc, "grand_cru_aocs": gc, "grand_cru_subdenominations": suffix,
    }
    collisions = defaultdict(list)
    for obs in catalog.world_area:
        collisions[normalize_name(obs.prime_name)].append({"source_name": obs.prime_name, "source_row": obs.source_row})
    groups = [{"search_key": k, "rows": v, "policy": "retain_source_rows_no_automatic_merge"}
              for k, v in sorted(collisions.items()) if len(v) > 1]
    ordered = sorted(catalog.world_area, key=lambda r: (
        0 if (r.area_2023_ha or 0) > 0 else 1 if r.latest_positive_area_ha else 2,
        -(r.area_2023_ha or r.latest_positive_area_ha or 0), r.prime_name, r.source_row))
    batch = [{"observation": asdict(r), "identity": asdict(resolver.resolve(r.prime_name, source_id=r.source_id))}
             for r in ordered[:batch_size]]
    identity = {
        "schema_version": "1.0", "snapshot_version": resolver.snapshot_version,
        "scope": "Offline evidence evaluation; this is not a completed live VIVC lookup batch",
        "summary": {"world_source_rows": len(catalog.world_area),
                    "resolved_country_rows": len(catalog.country_area),
                    "unresolved_country_rows": len(catalog.unresolved_country_area),
                    "country_source_rows_total": len(catalog.country_area) + len(catalog.unresolved_country_area),
                    "normalization_collision_groups": len(groups),
                    "catalog_ambiguous_search_keys": sum(len(v) > 1 for v in catalog.grape_name_candidates.values()),
                    "batch_rows": len(batch), "batch_status_counts": dict(Counter(r["identity"]["status"] for r in batch)),
                    "batch_confirmed": sum(r["identity"]["status"] == "RESOLVED" for r in batch)},
        "collision_groups": groups, "batch": batch,
        "unresolved_country_observations": [asdict(r) for r in catalog.unresolved_country_area],
    }
    inputs = sorted(HANDOFF.glob("*.json")) + [DATA / n for n in (
        "adelaide_world_varieties_2000_2023.csv", "adelaide_country_varieties_2000_2023.csv",
        "variety_identity_evidence.json")]
    for pattern in ("named_sites_*.json", "site_claim_rules_*.json", "legal_gi_specs_*.json"):
        inputs.extend(sorted(DATA.glob(pattern)))
    hashes = {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in inputs}
    burgundy["input_sha256"] = hashes
    identity["input_sha256"] = hashes
    return burgundy, identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=250)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 1998:
        parser.error("batch size must be between 1 and 1998")
    reports = build_reports(args.batch_size)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, doc in zip(("burgundy_reconciliation.json", "variety_identity_batch_001.json"), reports):
        (args.output_dir / name).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(name + ": " + json.dumps(doc["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
