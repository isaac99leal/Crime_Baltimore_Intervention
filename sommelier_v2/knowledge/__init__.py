"""Provenance-aware wine knowledge layer for Sommelier Simulator v2."""

from .aging import modified_archetype, state_at_age
from .catalog import SOURCES, WineKnowledgeCatalog, normalize_name
from .priors import SimulationPriors
from .schema import *  # noqa: F401,F403 - package intentionally exposes schema types
from .vintage import load_legacy_vintage_knowledge, vintage_stats

__all__ = [
    "SOURCES",
    "SimulationPriors",
    "WineKnowledgeCatalog",
    "load_legacy_vintage_knowledge",
    "modified_archetype",
    "normalize_name",
    "state_at_age",
    "vintage_stats",
]
