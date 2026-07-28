#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.schedule import is_collect_business_hour


def main() -> int:
    if is_collect_business_hour():
        print("Collect window: Kyiv business hours — run")
        return 0
    print("Collect window: outside Kyiv 09:00-18:00 — skip")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
