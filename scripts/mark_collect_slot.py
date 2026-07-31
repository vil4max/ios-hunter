#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.schedule import _as_kyiv, due_collect_slot
from database.collect_slots import default_collect_slots_path, mark_slot_completed


def main() -> int:
    stamp = _as_kyiv()
    due = due_collect_slot(stamp)
    if due is None:
        print("No due collect slot to mark")
        return 0
    day = stamp.strftime("%Y-%m-%d")
    path = default_collect_slots_path(ROOT)
    created = mark_slot_completed(path, day, due)
    if created:
        print(f"Marked Kyiv collect slot {due:02d} for {day}")
    else:
        print(f"Kyiv collect slot {due:02d} already marked for {day}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
