#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import load_settings
from planner.plan import ARCHIVE_HISTORY_MIN_DAYS, archived_age_days
from project_sync.archive_history import migrate_archived_to_history


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Move Archived Project cards older than N days into History."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List stale Archived cards without updating Project status.",
    )
    parser.add_argument(
        "--min-days",
        type=int,
        default=ARCHIVE_HISTORY_MIN_DAYS,
        help=f"Minimum archived age in days (default: {ARCHIVE_HISTORY_MIN_DAYS}).",
    )
    args = parser.parse_args()

    settings = load_settings()
    if not settings.configured_for_sync:
        print(
            "Archive migration requires Sync config "
            "(CAREER_AGENT_SYNC_ENABLED, CAREER_AGENT_TOKEN, project owner/number).",
            file=sys.stderr,
        )
        return 1

    stale = migrate_archived_to_history(
        settings,
        min_days=args.min_days,
        apply=not args.dry_run,
    )
    mode = "would move" if args.dry_run else "moved"
    print(f"{mode} {len(stale)} Archived card(s) to History (>= {args.min_days} days)")
    for card in stale:
        age = archived_age_days(card, __import__("datetime").date.today())
        age_label = f"{age}d" if age is not None else "unknown age"
        print(f"- {card.display_title} [{age_label}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
