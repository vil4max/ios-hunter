from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from database.repository import JobRecord

from apply.pack import process_actionable
from database.repository import JobRepository
from integrations.telegram import send_message
from parser.activity import ActivitySummary
from parser.diff import JobChange
from statistics.company_watch import find_hiring_sprees, render_company_watch


def apply_job_change(
    repo: JobRepository,
    run_id: int,
    record: JobRecord,
    change: JobChange,
    profile: dict[str, Any],
    now: str,
    activity: ActivitySummary,
) -> bool:
    if change.change_type == "new":
        activity.new += 1
        activity.changes.append(change)
        repo.add_history(record.id, "created")
        repo.add_run_activity(run_id, record.id, "new", record.company, record.title, record.url)
        return process_actionable(repo, record, "new", profile, now)

    if change.change_type == "reopened":
        activity.reopened += 1
        activity.changes.append(change)
        repo.add_history(record.id, "reopened")
        repo.add_run_activity(run_id, record.id, "reopened", record.company, record.title, record.url)
        return process_actionable(repo, record, "reopened", profile, now)

    if change.change_type == "updated":
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
        return process_actionable(repo, record, "updated", profile, now)

    return False


def close_missing_jobs(
    repo: JobRepository,
    run_id: int,
    seen_ids: set[str],
    now: str,
    activity: ActivitySummary,
) -> None:
    for job in repo.list_open_jobs():
        if job.id in seen_ids:
            continue
        repo.mark_closed(job.id, now)
        activity.closed += 1
        repo.add_history(job.id, "closed")
        repo.add_run_activity(run_id, job.id, "closed", job.company, job.title, job.url)


def send_company_watch_alerts(repo: JobRepository, root: Path) -> int:
    company_alerts = find_hiring_sprees(repo)
    company_watch_report = render_company_watch(company_alerts)
    if not company_watch_report:
        return 0

    report_path = root / "reports/company_watch/latest.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(company_watch_report + "\n", encoding="utf-8")

    telegram_ready = bool(os.environ.get("TELEGRAM_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))
    sent = 0
    for alert in company_alerts:
        if repo.company_watch_alerted_before(alert.company):
            continue
        if telegram_ready:
            send_message(render_company_watch([alert]))
        repo.record_company_watch_alert(alert.company)
        sent += 1
    return sent
