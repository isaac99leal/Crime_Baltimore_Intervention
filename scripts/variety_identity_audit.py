from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sommelier_v2.knowledge.variety_identity import VarietyIdentityRegistry  # noqa: E402
DEFAULT_CSV = ROOT / "sommelier_v2" / "knowledge" / "data" / "adelaide_world_varieties_2000_2023.csv"


def build_metrics(csv_path: Path = DEFAULT_CSV) -> dict[str, object]:
    registry = VarietyIdentityRegistry()
    rows: list[dict[str, object]] = []
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "name": row["prime"],
                    "area_2000_ha": float(row["area_2000_ha"] or 0.0),
                    "area_2010_ha": float(row["area_2010_ha"] or 0.0),
                    "area_2016_ha": float(row["area_2016_ha"] or 0.0),
                    "area_2023_ha": float(row["area_2023_ha"] or 0.0),
                }
            )

    counts = {level: 0 for level in ("R0", "R1", "R2", "R3", "R4", "R5")}
    resolved_2023 = 0.0
    total_2023 = 0.0
    resolved_history = 0.0
    total_history = 0.0
    unresolved: list[dict[str, object]] = []

    for row in rows:
        name = str(row["name"])
        decision = registry.resolve(name, source_id="adelaide_2025")
        counts[decision.level] = counts.get(decision.level, 0) + 1
        area_2023 = float(row["area_2023_ha"])
        history = sum(
            float(row[key])
            for key in ("area_2000_ha", "area_2010_ha", "area_2016_ha", "area_2023_ha")
        )
        total_2023 += area_2023
        total_history += history
        if decision.identity_confirmed:
            resolved_2023 += area_2023
            resolved_history += history
        else:
            unresolved.append(
                {
                    "name": name,
                    "area_2023_ha": area_2023,
                    "status": decision.status,
                    "level": decision.level,
                }
            )

    unresolved.sort(key=lambda row: float(row["area_2023_ha"]), reverse=True)

    return {
        "source_id": "adelaide_2025",
        "source_rows": len(rows),
        "resolution_counts": counts,
        "strong_links": counts["R4"] + counts["R5"],
        "total_2023_ha": total_2023,
        "resolved_2023_ha": resolved_2023,
        "resolved_2023_pct": (resolved_2023 / total_2023 * 100.0) if total_2023 else 0.0,
        "resolved_historical_pct": (resolved_history / total_history * 100.0) if total_history else 0.0,
        "unresolved_gt_10000_ha": [
            row for row in unresolved if float(row["area_2023_ha"]) > 10000.0
        ],
        "unresolved_gt_1000_ha_count": sum(
            1 for row in unresolved if float(row["area_2023_ha"]) > 1000.0
        ),
        "top_unresolved": unresolved[:30],
    }


def main() -> None:
    print(json.dumps(build_metrics(), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
