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
    EuLegalPromotionRegistry,
    JurisdictionLabelValidator,
    LegalAwareRegionGrapeRulebook,
    LegalSourceRegistry,
    SimulationPriors,
    WineKnowledgeCatalog,
    WorldWineKnowledgeCatalog,
    load_legacy_vintage_knowledge,
    vintage_stats,
)


def main() -> None:
    catalog = WineKnowledgeCatalog()
    world = WorldWineKnowledgeCatalog()
    rules = LegalAwareRegionGrapeRulebook(catalog=world)
    legal_sources = LegalSourceRegistry()
    promotions = EuLegalPromotionRegistry(rules.machine_constraints)
    labels = JurisdictionLabelValidator()
    priors = SimulationPriors()
    vintages = load_legacy_vintage_knowledge()
    stats = {}
    stats.update(catalog.stats())
    stats.update(world.stats())
    stats.update(rules.stats())
    stats.update(legal_sources.stats())
    stats.update(promotions.stats())
    stats.update(labels.stats())
    stats.update(vintage_stats(vintages))
    stats.update(priors.stats())
    print("KNOWLEDGE_AUDIT=" + json.dumps(stats, sort_keys=True))


if __name__ == "__main__":
    main()
