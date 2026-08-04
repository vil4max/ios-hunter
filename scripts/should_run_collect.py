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
    due_collect_slot,
    is_final_collect_slot,
)
from database.collect_slots import default_collect_slots_path, slot_completed
from database.daily_email_days import default_daily_email_days_path, email_sent_for_day


def main() -> int:
    stamp = _as_kyiv()
    due = due_collect_slot(stamp)
    day = stamp.strftime("%Y-%m-%d")
    final_slot = is_final_collect_slot(stamp)
    email_pending = final_slot and not email_sent_for_day(
        default_daily_email_days_path(ROOT), day
    )
    print(f"kyiv_hour={stamp.hour}")
    print(f"due_slot={due if due is not None else ''}")
    print(f"final_slot={'true' if final_slot else 'false'}")
    print(f"dispatch_daily_email={'true' if email_pending else 'false'}")
    if due is None:
        print("Collect window: before Kyiv 09:00 — skip")
        return 1
    path = default_collect_slots_path(ROOT)
    if slot_completed(path, day, due):
        print(f"Collect window: Kyiv slot {due:02d} already completed — skip")
        return 1
    slots = "/".join(f"{hour:02d}" for hour in COLLECT_HOURS)
    print(f"Collect window: Kyiv {slots} — run due slot {due:02d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
