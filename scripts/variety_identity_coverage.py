#!/usr/bin/env python3
"""Measure reviewed identity coverage without pooling countries or census years."""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sommelier_v2.knowledge.expanded_catalog import WorldWineKnowledgeCatalog
from sommelier_v2.knowledge.variety_identity import DATA_DIR, VarietyIdentityRegistry


def measure(observations, resolver):
    rows = [(o, resolver.resolve(o.prime_name, source_id=o.source_id, country=o.country)) for o in observations]
    counts = Counter(d.level for _, d in rows)
    years = {}
    for year in (2000, 2010, 2016, 2023):
        def area(o):
            return max(getattr(o, f'area_{year}_ha') or 0, 0)
        total = sum(area(o) for o, _ in rows)
        resolved = sum(area(o) for o, d in rows if d.identity_confirmed)
        years[str(year)] = dict(reported_positive_area_ha=round(total, 3),
                                resolved_area_ha=round(resolved, 3),
                                resolved_percent=round(100 * resolved / total, 4) if total else None,
                                missing_area_rows=sum(getattr(o, f'area_{year}_ha') is None for o, _ in rows))
    unresolved = [dict(observation=asdict(o), identity=asdict(d)) for o, d in rows if not d.identity_confirmed]
    unresolved.sort(key=lambda r: (-(r['observation']['area_2023_ha'] or 0), r['observation']['prime_name'], r['observation']['source_row'] or 0))
    conflicts = [dict(source_id=o.source_id, source_name=o.prime_name, source_row=o.source_row,
                      country=o.country, candidate_ids=d.candidate_ids, evidence_ids=d.evidence_ids,
                      conflict_class='competing_identity_evidence', status='open',
                      generator_policy='block_identity_promotion') for o, d in rows if d.status == 'CONFLICT']
    return dict(source_rows=len(rows), level_counts={f'R{i}': counts[f'R{i}'] for i in range(6)},
                area_by_census_year=years, conflict_count=len(conflicts), conflicts=conflicts,
                unresolved_over_10000ha_2023=sum((r['observation']['area_2023_ha'] or 0) > 10000 for r in unresolved),
                unresolved_over_1000ha_2023=sum((r['observation']['area_2023_ha'] or 0) > 1000 for r in unresolved),
                unresolved_queue=unresolved)


def build_report():
    catalog, resolver = WorldWineKnowledgeCatalog(), VarietyIdentityRegistry()
    report = measure(catalog.world_area, resolver)
    report['unresolved_queue_total'] = len(report['unresolved_queue'])
    report['unresolved_queue'] = report['unresolved_queue'][:50]
    report['queue_scope'] = 'Top 50 unresolved rows by reported 2023 hectares; summary counts cover all rows.'
    report.update(schema_version='1.0', snapshot_versions=resolver.snapshot_versions,
                  scope='Global Adelaide source rows only; country observations are not added to global totals.',
                  interpretation='Coverage is of reported positive hectares per census year, not distinct botanical varieties. Missing areas remain missing. R0 counts only actual resolver conflicts; unknown evidence is R1.',
                  input_sha256={str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in sorted([
                      DATA_DIR / 'adelaide_world_varieties_2000_2023.csv',
                      *DATA_DIR.glob('variety_identity_evidence*.json')])})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in {'unresolved_queue', 'input_sha256'}}, ensure_ascii=False))
