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
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
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


def detect_salary_change(old: str | None, new: str | None) -> bool:
    pattern = r"(\$|€|usd|eur|грн|uah)\s*\d"
    old_match = bool(re.search(pattern, (old or "").lower()))
    new_match = bool(re.search(pattern, (new or "").lower()))
    return old_match != new_match or (old or "") != (new or "")


def compare_job(existing: JobRecord | None, incoming: Vacancy, now: str) -> tuple[JobRecord, JobChange]:
    job_id = existing.id if existing else incoming.hash

    if existing is None:
        record = JobRecord(
            id=job_id,
            company=incoming.company,
            title=incoming.title,
            location=incoming.location,
            remote=incoming.remote,
            url=incoming.url,
            source=incoming.source,
            published_at=incoming.published_at.isoformat() if incoming.published_at else None,
            updated_at=now,
            first_seen=now,
            last_seen=now,
            status="open",
            description=incoming.description,
            hash=incoming.hash,
        )
        return record, JobChange(job_id=job_id, change_type="new")

    if existing.status == "closed":
        record = JobRecord(
            id=existing.id,
            company=incoming.company,
            title=incoming.title,
            location=incoming.location,
            remote=incoming.remote,
            url=incoming.url,
            source=incoming.source,
            published_at=existing.published_at,
            updated_at=now,
            first_seen=existing.first_seen,
            last_seen=now,
            status="open",
            description=incoming.description or existing.description,
            hash=existing.hash,
        )
        return record, JobChange(job_id=job_id, change_type="reopened")

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
        source=incoming.source,
        published_at=existing.published_at,
        updated_at=now,
        first_seen=existing.first_seen,
        last_seen=now,
        status="open",
        description=incoming.description or existing.description,
        hash=existing.hash,
    )
    return record, JobChange(
        job_id=job_id,
        change_type=change_type,
        change_summary=summary,
        diff=diff,
        old_description=existing.description,
        new_description=incoming.description,
    )
