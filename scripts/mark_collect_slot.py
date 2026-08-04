#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.schedule import FINAL_COLLECT_HOUR, _as_kyiv, due_collect_slot
from database.collect_slots import default_collect_slots_path, mark_slot_completed
from database.daily_email_days import default_daily_email_days_path, email_sent_for_day


def _write_github_output(**values: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT", "").strip()
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    stamp = _as_kyiv()
    due = due_collect_slot(stamp)
    day = stamp.strftime("%Y-%m-%d")
    if due is None:
        print("No due collect slot to mark")
        _write_github_output(
            marked_slot="",
            final_slot="false",
            dispatch_daily_email="false",
            kyiv_day=day,
        )
        return 0
    path = default_collect_slots_path(ROOT)
    created = mark_slot_completed(path, day, due)
    if created:
        print(f"Marked Kyiv collect slot {due:02d} for {day}")
    else:
        print(f"Kyiv collect slot {due:02d} already marked for {day}")
    final_slot = due == FINAL_COLLECT_HOUR
    email_pending = final_slot and not email_sent_for_day(
        default_daily_email_days_path(ROOT), day
    )
    _write_github_output(
        marked_slot=str(due),
        final_slot="true" if final_slot else "false",
        dispatch_daily_email="true" if email_pending else "false",
        kyiv_day=day,
    )
    print(f"final_slot={'true' if final_slot else 'false'}")
    print(f"dispatch_daily_email={'true' if email_pending else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
