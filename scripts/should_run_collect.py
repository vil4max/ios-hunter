#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.schedule import (
    COLLECT_HOURS,
    _as_kyiv,
    is_collect_business_hour,
    is_final_collect_slot,
)


def main() -> int:
    stamp = _as_kyiv()
    print(f"kyiv_hour={stamp.hour}")
    print(f"final_slot={'true' if is_final_collect_slot(stamp) else 'false'}")
    if is_collect_business_hour(stamp):
        slots = "/".join(f"{hour:02d}" for hour in COLLECT_HOURS)
        print(f"Collect window: Kyiv {slots} — run")
        return 0
    print("Collect window: outside Kyiv 09/12/15/18 — skip")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
