#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apply.matcher import load_profile
from apply.pack import process_actionable
from collector.companies import collect_all
from collector.description import fetch_description, should_fetch
from collector.health import render_health_report
from crm.followups import send_followup_reminders
from database.repository import JobRepository, utc_now
from integrations.public_reports import generate_rss, generate_weekly_report
from integrations.telegram import send_message
from parser.activity import ActivitySummary
from parser.deduplicate import deduplicate
from parser.diff import compare_job
from parser.normalize import Vacancy, normalize_many
from parser.skills import load_skills, sync_job_skills
from statistics.company_watch import find_hiring_sprees, render_company_watch
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


def main() -> int:
    started = time.perf_counter()
    started_at = utc_now()
    db_path = Path(os.environ.get("JOBS_DB_PATH", "database/jobs.db"))
    repo = JobRepository(db_path)
    profile = load_profile(ROOT / "config/profile.yaml")
    skills_map = load_skills(ROOT / "config/skills.yaml")
    run_id = repo.start_run_metrics(started_at)

    source_results = collect_all(ROOT / "database/swift_export.json")
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
    seen_ids: set[str] = set()
    activity = ActivitySummary()
    packs_sent = 0

    for vacancy in vacancies:
        existing = repo.get_job_by_hash(vacancy.hash)
        record, change = compare_job(existing, vacancy, now)
        repo.upsert_job(record)
        seen_ids.add(record.id)

        if record.description:
            sync_job_skills(repo, record.id, f"{record.title} {record.description}", skills_map)

        if change.change_type == "new":
            activity.new += 1
            activity.changes.append(change)
            repo.add_history(record.id, "created")
            repo.add_run_activity(run_id, record.id, "new", record.company, record.title, record.url)
            if process_actionable(repo, record, "new", profile, now):
                packs_sent += 1
        elif change.change_type == "reopened":
            activity.reopened += 1
            activity.changes.append(change)
            repo.add_history(record.id, "reopened")
            repo.add_run_activity(run_id, record.id, "reopened", record.company, record.title, record.url)
            if process_actionable(repo, record, "reopened", profile, now):
                packs_sent += 1
        elif change.change_type == "updated":
            activity.updated += 1
            activity.changes.append(change)
            repo.add_history(
                record.id,
                "description_changed",
                old_value=change.old_description,
                new_value=change.new_description,
                diff=change.diff,
            )
            repo.add_run_activity(
                run_id,
                record.id,
                "updated",
                record.company,
                record.title,
                record.url,
                change_summary=change.change_summary,
                diff=change.diff,
            )
            if process_actionable(repo, record, "updated", profile, now):
                packs_sent += 1

    for job in repo.list_open_jobs():
        if job.id not in seen_ids:
            repo.mark_closed(job.id, now)
            activity.closed += 1
            repo.add_history(job.id, "closed")
            repo.add_run_activity(run_id, job.id, "closed", job.company, job.title, job.url)

    company_alerts = find_hiring_sprees(repo)
    company_watch_report = render_company_watch(company_alerts)
    if company_watch_report:
        write_report(ROOT / "reports/company_watch/latest.md", company_watch_report)
        if os.environ.get("TELEGRAM_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
            for alert in company_alerts:
                if repo.company_watch_alerted_recently(alert.company):
                    continue
                send_message(render_company_watch([alert]))
                repo.record_company_watch_alert(alert.company)

    followups_sent = send_followup_reminders(repo)

    runtime = time.perf_counter() - started
    finished_at = utc_now()
    failed_sources = sum(1 for result in source_results if result.status == "failed")

    repo.finish_run_metrics(
        run_id,
        {
            "finished_at": finished_at,
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
    timeline_report = render_timeline_report(repo)

    activity_report = activity.render()
    health_report = render_health_report(source_results, runtime, duplicates_removed)
    summary = (
        f"{activity_report}\n\n{health_report}\n\n"
        f"Application packs sent: {packs_sent}\n"
        f"Company Watch alerts: {len(company_alerts)}\n"
        f"CRM follow-ups sent: {followups_sent}"
    )

    write_report(ROOT / "reports/activity/latest.md", activity_report)
    write_report(ROOT / "reports/health/latest.md", health_report)
    write_report(ROOT / "reports/market/snapshot.md", render_market_summary(market_summary))
    write_report(ROOT / "reports/timeline/market-timeline.md", timeline_report)
    generate_weekly_report(repo, ROOT)
    repo.export_jobs_json(ROOT / "database/jobs.json")
    repo.export_jobs_json(ROOT / "website/data/jobs.json")
    generate_rss(repo, ROOT / "website/feed.xml")

    write_report(
        ROOT / "website/data/activity.json",
        json.dumps(
            {
                "headline": activity.headline(),
                "new": activity.new,
                "updated": activity.updated,
                "closed": activity.closed,
                "reopened": activity.reopened,
                "actionable": activity.actionable,
                "packs_sent": packs_sent,
                "company_watch_alerts": len(company_alerts),
            },
            indent=2,
        ),
    )

    write_report(
        ROOT / "website/data/market.json",
        json.dumps(
            {
                "open_jobs": market_summary.open_jobs,
                "remote": market_summary.remote,
                "hybrid": market_summary.hybrid,
                "onsite": market_summary.onsite,
                "new_this_week": market_summary.new_this_week,
                "closed_this_week": market_summary.closed_this_week,
                "top_companies": [
                    {"company": company, "open_jobs": count}
                    for company, count in market_summary.top_companies
                ],
            },
            indent=2,
        ),
    )

    print(summary)
    repo.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
