#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import load_settings
from database.seen import default_seen_path, load_seen
from parser.normalize import Vacancy
from project_sync.sync import ProjectSync


def vacancies_from_seen(seen: dict) -> list[Vacancy]:
    vacancies: list[Vacancy] = []
    for url, meta in seen.items():
        if not isinstance(meta, dict):
            continue
        company = str(meta.get("company") or "Unknown")
        title = str(meta.get("title") or "Vacancy")
        vacancies.append(
            Vacancy(
                company=company,
                title=title,
                url=str(url),
                source="seen-seed",
            )
        )
    return vacancies


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed GitHub Project with Archived cards from database/seen.json (no Telegram)."
    )
    parser.add_argument(
        "--seen-path",
        type=Path,
        default=Path(os.environ.get("SEEN_PATH", default_seen_path(ROOT))),
    )
    parser.add_argument("--dry-run", action="store_true", help="Print counts only; do not call GitHub.")
    args = parser.parse_args()

    settings = load_settings()
    seen = load_seen(args.seen_path)
    vacancies = vacancies_from_seen(seen)
    print(f"Seen entries: {len(vacancies)}")

    if args.dry_run:
        for vacancy in vacancies[:20]:
            print(f"- {vacancy.company} — {vacancy.title} :: {vacancy.canonical_url}")
        if len(vacancies) > 20:
            print(f"... +{len(vacancies) - 20}")
        return 0

    if not settings.configured_for_sync:
        print(
            "Sync is not configured. Set CAREER_AGENT_SYNC_ENABLED=1, CAREER_AGENT_TOKEN, "
            "GITHUB_REPOSITORY, GITHUB_PROJECT_OWNER, GITHUB_PROJECT_NUMBER.",
            file=sys.stderr,
        )
        return 1

    result = ProjectSync(settings).seed_archived(vacancies)
    print(
        f"Created: {result.created_count}\n"
        f"Existing: {result.existing_count}\n"
        f"Failed: {result.failed_count}"
    )
    for item in result.failed:
        print(f"FAIL {item.canonical_url}: {item.error}", file=sys.stderr)
    return 1 if result.failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
