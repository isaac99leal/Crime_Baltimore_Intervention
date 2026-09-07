#!/usr/bin/env python3
"""Audit bulk operational coverage of the Adelaide world-variety universe."""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sommelier_v2.knowledge.variety_bulk import BulkVarietyRegistry  # noqa: E402


def main() -> None:
    registry = BulkVarietyRegistry()
    stats = registry.stats()
    print("VARIETY_BULK_AUDIT=" + json.dumps(stats, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
