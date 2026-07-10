#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collector.companies import collect_all
from database.seen import (
    default_seen_path,
    load_seen,
    mark_seen,
    migrate_from_sqlite,
    save_seen,
    seen_key,
    utc_now,
)
from integrations.notify import notify_vacancy
from parser.deduplicate import deduplicate_with_report
from parser.normalize import Vacancy, normalize_many


def collect_vacancies(swift_export_path: Path) -> tuple[list[Vacancy], int, int]:
    collect_result = collect_all(swift_export_path)
    raw_jobs: list[dict] = []
    failed_sources = 0
    for source in collect_result.source_results:
        if source.status == "failed":
            failed_sources += 1
            print(f"Source failed: {source.company}: {source.error}", file=sys.stderr)
            continue
        raw_jobs.extend(source.jobs)

    vacancies = normalize_many(raw_jobs)
    unique, removed, _ = deduplicate_with_report(vacancies)
    return unique, removed, failed_sources


def process_new_vacancies(
    vacancies: list[Vacancy],
    seen: dict,
    *,
    seed_only: bool,
) -> tuple[int, int]:
    sent = 0
    marked = 0
    now = utc_now()

    for vacancy in vacancies:
        key = seen_key(vacancy)
        if not key or key in seen:
            continue
        if not seed_only:
            try:
                notify_vacancy(vacancy)
                sent += 1
            except Exception as error:
                print(
                    f"Telegram send failed for {vacancy.company} / {vacancy.title}: {error}",
                    file=sys.stderr,
                )
                continue
        if mark_seen(seen, vacancy, first_seen=now):
            marked += 1

    return sent, marked


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect iOS vacancies and notify Telegram of new ones.")
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Mark all current vacancies as seen without sending Telegram messages.",
    )
    args = parser.parse_args()

    seed_only = args.seed_only or os.environ.get("SEED_SEEN_ONLY", "").strip() in {"1", "true", "yes"}
    seen_path = Path(os.environ.get("SEEN_PATH", default_seen_path(ROOT)))
    swift_export = Path(os.environ.get("SWIFT_EXPORT_PATH", ROOT / "database" / "swift_export.json"))
    jobs_db = Path(os.environ.get("JOBS_DB_PATH", ROOT / "database" / "jobs.db"))

    started = time.perf_counter()
    seen = load_seen(seen_path)

    migrated = 0
    if not seen:
        migrated = migrate_from_sqlite(jobs_db, seen)
        if migrated:
            print(f"Migrated {migrated} vacancies from {jobs_db} into seen store.")

    vacancies, duplicates_removed, failed_sources = collect_vacancies(swift_export)
    sent, marked = process_new_vacancies(vacancies, seen, seed_only=seed_only)

    if migrated or marked:
        save_seen(seen_path, seen)

    runtime = time.perf_counter() - started
    print(
        f"Vacancies: {len(vacancies)}\n"
        f"Duplicates removed: {duplicates_removed}\n"
        f"Sources failed: {failed_sources}\n"
        f"New notified: {sent}\n"
        f"Newly marked seen: {marked}\n"
        f"Seed only: {seed_only}\n"
        f"Seen total: {len(seen)}\n"
        f"Runtime: {runtime:.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
