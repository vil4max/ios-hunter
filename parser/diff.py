from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

from database.repository import JobRecord
from parser.normalize import Vacancy


@dataclass
class JobChange:
    job_id: str
    change_type: str
    change_summary: str | None = None
    diff: str | None = None
    old_description: str | None = None
    new_description: str | None = None


def line_diff(old: str | None, new: str | None) -> str:
    old_lines = (old or "").splitlines()
    new_lines = (new or "").splitlines()
    diff_lines = []
    for line in difflib.unified_diff(old_lines, new_lines, lineterm=""):
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+"):
            diff_lines.append(f"+ {line[1:]}")
        elif line.startswith("-"):
            diff_lines.append(f"- {line[1:]}")
    return "\n".join(diff_lines)


def summarize_diff(diff: str) -> str:
    if not diff:
        return ""
    added = [line[2:].strip() for line in diff.splitlines() if line.startswith("+ ")]
    return ", ".join(added[:3])


def _record_from_vacancy(incoming: Vacancy, now: str, job_id: str, status: str = "open") -> JobRecord:
    return JobRecord(
        id=job_id,
        company=incoming.company,
        title=incoming.title,
        location=incoming.location,
        remote=incoming.remote,
        url=incoming.url,
        canonical_url=incoming.canonical_url,
        source=incoming.source,
        source_job_id=incoming.source_job_id,
        identity_strategy=incoming.identity_strategy or "unknown",
        identity_key=incoming.identity_key or job_id,
        published_at=incoming.published_at.isoformat() if incoming.published_at else None,
        updated_at=now,
        first_seen=now,
        last_seen=now,
        status=status,
        description=incoming.description,
        hash=incoming.hash,
    )


def _compare_new(incoming: Vacancy, now: str) -> tuple[JobRecord, JobChange]:
    job_id = incoming.identity_key or incoming.hash
    record = _record_from_vacancy(incoming, now, job_id)
    return record, JobChange(job_id=job_id, change_type="new")


def _compare_reopened(existing: JobRecord, incoming: Vacancy, now: str) -> tuple[JobRecord, JobChange]:
    record = JobRecord(
        id=existing.id,
        company=incoming.company,
        title=incoming.title,
        location=incoming.location,
        remote=incoming.remote,
        url=incoming.url,
        canonical_url=incoming.canonical_url,
        source=incoming.source,
        source_job_id=incoming.source_job_id,
        identity_strategy=existing.identity_strategy,
        identity_key=existing.identity_key,
        published_at=existing.published_at,
        updated_at=now,
        first_seen=existing.first_seen,
        last_seen=now,
        status="open",
        description=incoming.description or existing.description,
        hash=existing.hash,
    )
    return record, JobChange(job_id=existing.id, change_type="reopened")


def _compare_existing(existing: JobRecord, incoming: Vacancy, now: str) -> tuple[JobRecord, JobChange]:
    description_changed = (existing.description or "") != (incoming.description or "")
    title_changed = existing.title != incoming.title
    remote_changed = (existing.remote or "") != (incoming.remote or "")

    diff = None
    summary = None
    change_type = "unchanged"

    if description_changed or title_changed or remote_changed:
        change_type = "updated"
        diff = line_diff(existing.description, incoming.description)
        if title_changed:
            diff = (diff + "\n" if diff else "") + f"+ title: {incoming.title}\n- title: {existing.title}"
        summary = summarize_diff(diff) or "requirements updated"

    record = JobRecord(
        id=existing.id,
        company=incoming.company,
        title=incoming.title,
        location=incoming.location or existing.location,
        remote=incoming.remote or existing.remote,
        url=incoming.url,
        canonical_url=incoming.canonical_url,
        source=incoming.source,
        source_job_id=incoming.source_job_id or existing.source_job_id,
        identity_strategy=existing.identity_strategy,
        identity_key=existing.identity_key,
        published_at=existing.published_at,
        updated_at=now,
        first_seen=existing.first_seen,
        last_seen=now,
        status="open",
        description=incoming.description or existing.description,
        hash=existing.hash,
    )
    return record, JobChange(
        job_id=existing.id,
        change_type=change_type,
        change_summary=summary,
        diff=diff,
        old_description=existing.description,
        new_description=incoming.description,
    )


def compare_job(existing: JobRecord | None, incoming: Vacancy, now: str) -> tuple[JobRecord, JobChange]:
    if existing is None:
        return _compare_new(incoming, now)
    if existing.status == "closed":
        return _compare_reopened(existing, incoming, now)
    return _compare_existing(existing, incoming, now)
