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
from integrations.notify import CollectReportStats, notify_empty_report, notify_new_vacancies
from parser.deduplicate import deduplicate_with_report
from parser.normalize import Vacancy, normalize_many


def collect_vacancies(swift_export_path: Path) -> tuple[list[Vacancy], int, list[str]]:
    collect_result = collect_all(swift_export_path)
    raw_jobs: list[dict] = []
    failed_source_names: list[str] = []
    for source in collect_result.source_results:
        if source.status == "failed":
            failed_source_names.append(source.source_name)
            print(f"Source failed: {source.source_name}: {source.error}", file=sys.stderr)
            continue
        raw_jobs.extend(source.jobs)

    if collect_result.swift_meta is not None:
        for company in collect_result.swift_meta.failed_companies:
            label = f"Swift: {company}"
            if label not in failed_source_names:
                failed_source_names.append(label)

    vacancies = normalize_many(raw_jobs)
    unique, removed, _ = deduplicate_with_report(vacancies)
    return unique, removed, failed_source_names


def process_new_vacancies(
    vacancies: list[Vacancy],
    seen: dict,
    *,
    seed_only: bool,
    duplicates_removed: int = 0,
    failed_source_names: list[str] | None = None,
) -> tuple[int, int]:
    now = utc_now()
    failed = tuple(failed_source_names or ())
    fresh: list[Vacancy] = []
    for vacancy in vacancies:
        key = seen_key(vacancy)
        if not key or key in seen:
            continue
        fresh.append(vacancy)

    stats = CollectReportStats(
        found=len(vacancies),
        seen_total=len(seen),
        new_count=len(fresh),
        duplicates_removed=duplicates_removed,
        failed_source_names=failed,
    )

    sent = 0
    if seed_only:
        pass
    elif fresh:
        try:
            sent = notify_new_vacancies(fresh, stats=stats)
        except Exception as error:
            print(f"Telegram send failed: {error}", file=sys.stderr)
            return 0, 0
    else:
        try:
            notify_empty_report(stats=stats)
        except Exception as error:
            print(f"Telegram send failed: {error}", file=sys.stderr)
            return 0, 0

    marked = 0
    if seed_only or sent:
        for vacancy in fresh:
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

    vacancies, duplicates_removed, failed_source_names = collect_vacancies(swift_export)
    sent, marked = process_new_vacancies(
        vacancies,
        seen,
        seed_only=seed_only,
        duplicates_removed=duplicates_removed,
        failed_source_names=failed_source_names,
    )

    if migrated or marked:
        save_seen(seen_path, seen)

    runtime = time.perf_counter() - started
    print(
        f"Vacancies: {len(vacancies)}\n"
        f"Duplicates removed: {duplicates_removed}\n"
        f"Sources failed: {len(failed_source_names)}\n"
        f"New notified: {sent}\n"
        f"Newly marked seen: {marked}\n"
        f"Seed only: {seed_only}\n"
        f"Seen total: {len(seen)}\n"
        f"Runtime: {runtime:.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
