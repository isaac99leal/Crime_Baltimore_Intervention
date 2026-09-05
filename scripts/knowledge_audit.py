#!/usr/bin/env python3
"""Print exact coverage for the v2 wine knowledge layer."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sommelier_v2.knowledge import (  # noqa: E402
    SimulationPriors,
    WineKnowledgeCatalog,
    load_legacy_vintage_knowledge,
    vintage_stats,
)


def main() -> None:
    catalog = WineKnowledgeCatalog()
    priors = SimulationPriors()
    vintages = load_legacy_vintage_knowledge()
    stats = {}
    stats.update(catalog.stats())
    stats.update(vintage_stats(vintages))
    stats.update(priors.stats())
    print("KNOWLEDGE_AUDIT=" + json.dumps(stats, sort_keys=True))


if __name__ == "__main__":
    main()
