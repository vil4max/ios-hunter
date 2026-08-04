#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.schedule import KYIV
from database.daily_email_days import (
    default_daily_email_days_path,
    email_sent_for_day,
    mark_email_sent,
    unmark_email_sent,
)


def _write_github_output(**values: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT", "").strip()
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    force = "--force" in sys.argv or os.environ.get("DAILY_EMAIL_FORCE", "").strip() in {
        "1",
        "true",
        "yes",
    }
    day = datetime.now(KYIV).strftime("%Y-%m-%d")
    path = default_daily_email_days_path(ROOT)
    if force and email_sent_for_day(path, day):
        unmark_email_sent(path, day)
        print(f"Force: unmarked daily email day {day}")
    if email_sent_for_day(path, day):
        print(f"Daily email already claimed for {day} — skip")
        _write_github_output(claimed="false", already="true", kyiv_day=day)
        return 0
    created = mark_email_sent(path, day)
    print(f"Claimed daily email day {day}" if created else f"Daily email day {day} already claimed")
    _write_github_output(claimed="true", already="false", kyiv_day=day)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
