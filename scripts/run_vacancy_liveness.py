#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import load_settings
from project_sync.liveness import run_vacancy_liveness
from reporter.vacancy_liveness import notify_vacancy_liveness


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check active Project vacancies for closed URLs, archive, Telegram status."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect closed vacancies without archiving Project cards.",
    )
    args = parser.parse_args()

    settings = load_settings()
    if not settings.configured_for_sync:
        print(
            "Vacancy liveness requires Sync config "
            "(CAREER_AGENT_SYNC_ENABLED, CAREER_AGENT_TOKEN, project owner/number, GITHUB_REPOSITORY).",
            file=sys.stderr,
        )
        return 1

    result = run_vacancy_liveness(
        settings,
        apply_archives=not args.dry_run,
    )
    notify_vacancy_liveness(
        result,
        board_url=settings.project_board_url,
    )
    archived = result.archived or []
    print(
        f"Checked={result.checked} skipped={result.skipped} "
        f"closed={len(result.closed or [])} archived={len(archived)} dry_run={args.dry_run}"
    )
    for hit in archived or (result.closed or []):
        label = hit.card.display_title
        print(f"- {label}: {hit.probe.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
