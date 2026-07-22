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
from collector.types import SourceResult
from config.settings import load_settings
from database.seen import (
    default_seen_path,
    load_seen,
    mark_seen,
    migrate_from_sqlite,
    save_seen,
    seen_key,
    utc_now,
)
from integrations.notify import CollectReportStats
from parser.deduplicate import deduplicate_with_report
from parser.normalize import Vacancy, normalize_many
from project_sync.sync import ProjectSync, SyncItemResult, SyncResult
from reporter.hourly import notify_hourly_inbox


def _is_telegram_source(source: SourceResult) -> bool:
    return source.source_id.startswith("telegram:") or source.source_name.startswith("Telegram @")


def _telegram_channel_label(source: SourceResult) -> str:
    if source.source_id.startswith("telegram:"):
        return source.source_id.split(":", 1)[1]
    if source.source_name.startswith("Telegram @"):
        return source.source_name.removeprefix("Telegram @").strip()
    return source.source_name


def summarize_source_checks(
    source_results: list[SourceResult],
    *,
    swift_failed_companies: list[str] | None = None,
) -> tuple[tuple[str, ...], dict[str, object]]:
    failed_names: list[str] = []
    sites_ok = 0
    sites_total = 0
    telegram_ok = 0
    telegram_total = 0
    telegram_skipped = 0
    telegram_ok_names: list[str] = []

    for source in source_results:
        if _is_telegram_source(source):
            telegram_total += 1
            skipped = bool(source.error and "not set" in source.error.lower())
            if source.status == "failed":
                failed_names.append(source.source_name)
            elif skipped:
                telegram_skipped += 1
            else:
                telegram_ok += 1
                telegram_ok_names.append(_telegram_channel_label(source))
            continue

        sites_total += 1
        if source.status == "failed":
            failed_names.append(source.source_name)
        else:
            sites_ok += 1

    for company in swift_failed_companies or []:
        label = f"Swift: {company}"
        if label not in failed_names:
            failed_names.append(label)

    health = {
        "sites_ok": sites_ok,
        "sites_total": sites_total,
        "telegram_ok": telegram_ok,
        "telegram_total": telegram_total,
        "telegram_skipped": telegram_skipped,
        "telegram_ok_names": tuple(telegram_ok_names),
    }
    return tuple(failed_names), health


def collect_vacancies(
    swift_export_path: Path,
) -> tuple[list[Vacancy], int, tuple[str, ...], dict[str, object]]:
    collect_result = collect_all(swift_export_path)
    raw_jobs: list[dict] = []
    for source in collect_result.source_results:
        if source.status == "failed":
            print(f"Source failed: {source.source_name}: {source.error}", file=sys.stderr)
            continue
        raw_jobs.extend(source.jobs)

    swift_failed = (
        list(collect_result.swift_meta.failed_companies)
        if collect_result.swift_meta is not None
        else []
    )
    for company in swift_failed:
        print(f"Source failed: Swift: {company}", file=sys.stderr)

    failed_source_names, health = summarize_source_checks(
        collect_result.source_results,
        swift_failed_companies=swift_failed,
    )
    vacancies = normalize_many(raw_jobs)
    unique, removed, _ = deduplicate_with_report(vacancies)
    return unique, removed, failed_source_names, health


def select_fresh(vacancies: list[Vacancy], seen: dict, *, seen_gate: bool) -> list[Vacancy]:
    if not seen_gate:
        return list(vacancies)
    fresh: list[Vacancy] = []
    for vacancy in vacancies:
        key = seen_key(vacancy)
        if not key or key in seen:
            continue
        fresh.append(vacancy)
    return fresh


def _mark_urls(seen: dict, vacancies: list[Vacancy], urls: set[str], *, first_seen: str) -> int:
    marked = 0
    for vacancy in vacancies:
        key = seen_key(vacancy)
        if key in urls and mark_seen(seen, vacancy, first_seen=first_seen):
            marked += 1
    return marked


def process_new_vacancies(
    vacancies: list[Vacancy],
    seen: dict,
    *,
    seed_only: bool,
    duplicates_removed: int = 0,
    failed_source_names: list[str] | tuple[str, ...] | None = None,
    source_health: dict[str, object] | None = None,
) -> tuple[int, int, SyncResult]:
    settings = load_settings()
    now = utc_now()
    failed = tuple(failed_source_names or ())
    health = source_health or {}
    fresh = select_fresh(vacancies, seen, seen_gate=settings.seen_gate_enabled)

    stats = CollectReportStats(
        found=len(vacancies),
        seen_total=len(seen),
        new_count=len(fresh),
        duplicates_removed=duplicates_removed,
        failed_source_names=failed,
        sites_ok=int(health.get("sites_ok", 0) or 0),
        sites_total=int(health.get("sites_total", 0) or 0),
        telegram_ok=int(health.get("telegram_ok", 0) or 0),
        telegram_total=int(health.get("telegram_total", 0) or 0),
        telegram_skipped=int(health.get("telegram_skipped", 0) or 0),
        telegram_ok_names=tuple(
            str(name) for name in (health.get("telegram_ok_names") or ())
        ),
    )

    if seed_only:
        sync_result = SyncResult(skipped_disabled=not settings.configured_for_sync)
        if settings.configured_for_sync and fresh:
            sync_result = ProjectSync(settings).seed_archived(fresh)
            ok_urls = {item.canonical_url for item in sync_result.created + sync_result.existing}
            marked = _mark_urls(seen, fresh, ok_urls, first_seen=now)
            return 0, marked, sync_result
        marked = 0
        for vacancy in fresh:
            if mark_seen(seen, vacancy, first_seen=now):
                marked += 1
        return 0, marked, sync_result

    if settings.configured_for_sync:
        sync_result = ProjectSync(settings).sync_vacancies(fresh, status_name="Inbox")
        try:
            notify_hourly_inbox(
                sync_result,
                fresh,
                stats=stats,
                board_url=settings.project_board_url,
            )
        except Exception as error:
            print(f"Telegram send failed: {error}", file=sys.stderr)
            return 0, 0, sync_result
        ok_urls = {item.canonical_url for item in sync_result.created + sync_result.existing}
        marked = _mark_urls(seen, fresh, ok_urls, first_seen=now)
        return sync_result.created_count, marked, sync_result

    sync_result = SyncResult(
        skipped_disabled=True,
        created=[
            SyncItemResult(
                canonical_url=seen_key(v),
                company=v.company,
                title=v.title,
                created=True,
            )
            for v in fresh
            if seen_key(v)
        ],
    )
    try:
        notify_hourly_inbox(
            sync_result,
            fresh,
            stats=stats,
            board_url=settings.project_board_url,
        )
    except Exception as error:
        print(f"Telegram send failed: {error}", file=sys.stderr)
        return 0, 0, sync_result

    marked = 0
    for vacancy in fresh:
        if mark_seen(seen, vacancy, first_seen=now):
            marked += 1
    return len(fresh), marked, sync_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect iOS vacancies and sync Career Agent Inbox.")
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Mark current vacancies as seen (and seed Archived when Sync is enabled) without hourly alert.",
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

    vacancies, duplicates_removed, failed_source_names, source_health = collect_vacancies(swift_export)
    sent, marked, sync_result = process_new_vacancies(
        vacancies,
        seen,
        seed_only=seed_only,
        duplicates_removed=duplicates_removed,
        failed_source_names=failed_source_names,
        source_health=source_health,
    )

    if migrated or marked:
        save_seen(seen_path, seen)

    runtime = time.perf_counter() - started
    print(
        f"Vacancies: {len(vacancies)}\n"
        f"Duplicates removed: {duplicates_removed}\n"
        f"Sources failed: {len(failed_source_names)}\n"
        f"Inbox created: {sync_result.created_count}\n"
        f"Already in Project: {sync_result.existing_count}\n"
        f"Sync failed: {sync_result.failed_count}\n"
        f"Sync skipped: {sync_result.skipped_disabled}\n"
        f"Hourly notified count: {sent}\n"
        f"Newly marked seen: {marked}\n"
        f"Seed only: {seed_only}\n"
        f"Seen total: {len(seen)}\n"
        f"Runtime: {runtime:.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
