#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apply.matcher import load_profile
from collector.companies import collect_all
from collector.description import fetch_description, should_fetch
from collector.health import render_health_report
from collector.types import SourceResult, SwiftCollectorMeta
from crm.followups import send_followup_reminders
from database.repository import JobRepository, utc_now
from integrations.monitor_digest import send_monitor_digest
from integrations.public_reports import generate_companies_report, generate_weekly_report
from parser.activity import ActivitySummary
from parser.deduplicate import deduplicate
from parser.diff import compare_job
from parser.normalize import Vacancy, normalize_many
from parser.pipeline_steps import apply_job_change, close_missing_jobs, send_company_watch_alerts
from parser.skills import load_skills, sync_job_skills
from statistics.engine import compute_market_summary, render_market_summary
from statistics.timeline import render_timeline_report, upsert_current_month_snapshot


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n", encoding="utf-8")


def enrich_descriptions(vacancies: list[Vacancy], limit: int = 15) -> None:
    fetched = 0
    for vacancy in vacancies:
        if vacancy.description or not should_fetch(vacancy.url):
            continue
        if fetched >= limit:
            break
        description = fetch_description(vacancy.url)
        if description:
            vacancy.description = description
            fetched += 1


def process_vacancies(
    repo: JobRepository,
    run_id: int,
    vacancies: list[Vacancy],
    profile: dict,
    skills_map: dict,
    now: str,
) -> tuple[ActivitySummary, set[str], int]:
    activity = ActivitySummary()
    seen_ids: set[str] = set()
    packs_sent = 0

    for vacancy in vacancies:
        existing = repo.get_job_by_hash(vacancy.hash)
        if existing is None:
            existing = repo.get_job_by_company_title(vacancy.company, vacancy.title)
        record, change = compare_job(existing, vacancy, now)
        repo.upsert_job(record)
        seen_ids.add(record.id)

        if record.description:
            sync_job_skills(repo, record.id, f"{record.title} {record.description}", skills_map)

        if change.change_type in {"new", "reopened", "updated"}:
            try:
                if apply_job_change(repo, run_id, record, change, profile, now, activity):
                    packs_sent += 1
            except Exception as error:
                print(
                    f"Actionable processing failed for {vacancy.company} / {vacancy.title}: {error}",
                    file=sys.stderr,
                )

    close_missing_jobs(repo, run_id, seen_ids, now, activity)
    return activity, seen_ids, packs_sent


def write_run_reports(repo: JobRepository, root: Path, market_summary: Any) -> None:
    write_report(root / "reports/market/snapshot.md", render_market_summary(market_summary))
    write_report(root / "reports/timeline/market-timeline.md", render_timeline_report(repo))
    generate_weekly_report(repo, root)
    generate_companies_report(repo, root)


def finalize_run(
    repo: JobRepository,
    run_id: int,
    activity: ActivitySummary,
    source_results: list[SourceResult],
    swift_meta: SwiftCollectorMeta | None,
    profile: dict,
    duplicates_removed: int,
    runtime: float,
    packs_sent: int,
    company_watch_alerts: int,
    followups_sent: int,
    pruned_jobs: int,
) -> bool:
    failed_sources = sum(1 for result in source_results if result.status == "failed")
    repo.finish_run_metrics(
        run_id,
        {
            "finished_at": utc_now(),
            "runtime_seconds": runtime,
            "sources_total": len(source_results),
            "sources_healthy": len(source_results) - failed_sources,
            "sources_failed": failed_sources,
            "new_jobs": activity.new,
            "updated_jobs": activity.updated,
            "closed_jobs": activity.closed,
            "reopened_jobs": activity.reopened,
            "actionable_jobs": activity.actionable,
            "duplicates_removed": duplicates_removed,
            "quality_warnings": 0,
        },
    )

    upsert_current_month_snapshot(repo)
    market_summary = compute_market_summary(repo)
    activity_report = activity.render()
    health_report = render_health_report(source_results, runtime, duplicates_removed, swift_meta)

    write_report(ROOT / "reports/activity/latest.md", activity_report)
    write_report(ROOT / "reports/health/latest.md", health_report)
    write_run_reports(repo, ROOT, market_summary)
    monitor_digest_sent = send_monitor_digest(repo, activity, source_results, profile, swift_meta)

    print(
        f"{activity_report}\n\n{health_report}\n\n"
        f"Application packs sent: {packs_sent}\n"
        f"Company Watch alerts: {company_watch_alerts}\n"
        f"CRM follow-ups sent: {followups_sent}\n"
        f"Monitor digest sent: {monitor_digest_sent}\n"
        f"Pruned jobs (retention): {pruned_jobs}"
    )
    return monitor_digest_sent


def main() -> int:
    started = time.perf_counter()
    started_at = utc_now()
    repo = JobRepository(Path(os.environ.get("JOBS_DB_PATH", "database/jobs.db")), base_dir=ROOT)
    profile = load_profile(ROOT / "config/profile.yaml")
    skills_map = load_skills(ROOT / "config/skills.yaml")
    run_id = repo.start_run_metrics(started_at)

    activity = ActivitySummary()
    source_results: list[SourceResult] = []
    swift_meta: SwiftCollectorMeta | None = None
    duplicates_removed = 0
    packs_sent = 0
    company_watch_alerts = 0
    followups_sent = 0
    pruned_jobs = 0
    pipeline_error: Exception | None = None

    try:
        collect_result = collect_all(ROOT / "database/swift_export.json")
        source_results = collect_result.source_results
        swift_meta = collect_result.swift_meta
        raw_jobs: list[dict] = []
        for result in source_results:
            repo.upsert_source_health(
                source_id=result.source_id,
                source_name=result.source_name,
                source_url=result.source_url,
                status=result.status,
                error=result.error,
                response_ms=result.response_ms,
                jobs_count=len(result.jobs),
            )
            raw_jobs.extend(result.jobs)

        vacancies = normalize_many(raw_jobs)
        enrich_descriptions(vacancies)
        vacancies, duplicates_removed = deduplicate(vacancies)
        now = utc_now()

        activity, _, packs_sent = process_vacancies(repo, run_id, vacancies, profile, skills_map, now)
        company_watch_alerts = send_company_watch_alerts(repo, ROOT)
        followups_sent = send_followup_reminders(repo)
        pruned_jobs = repo.prune_jobs_older_than(days=int(os.environ.get("JOBS_RETENTION_DAYS", "45")))
    except Exception as error:
        pipeline_error = error
        traceback.print_exc()
    finally:
        runtime = time.perf_counter() - started
        if source_results:
            finalize_run(
                repo,
                run_id,
                activity,
                source_results,
                swift_meta,
                profile,
                duplicates_removed,
                runtime,
                packs_sent,
                company_watch_alerts,
                followups_sent,
                pruned_jobs,
            )
        repo.close()

    if pipeline_error is not None:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
