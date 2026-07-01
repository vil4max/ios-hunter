from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from database.repository import JobRepository, utc_now


@dataclass
class ApplicationRecord:
    id: int
    job_id: str | None
    company: str
    title: str
    applied_at: str
    source: str
    resume_version: str | None
    stage: str
    follow_up_at: str | None


def log_application(
    repo: JobRepository,
    company: str,
    title: str,
    source: str,
    job_id: str | None = None,
    recruiter_id: int | None = None,
    resume_version: str | None = None,
    cover_letter: str | None = None,
    follow_up_days: int = 7,
) -> int:
    now = utc_now()
    follow_up = (datetime.now(timezone.utc) + timedelta(days=follow_up_days)).replace(microsecond=0).isoformat()
    cursor = repo._conn.execute(
        """
        INSERT INTO applications (
            job_id, company, title, recruiter_id, applied_at, source,
            resume_version, cover_letter, stage, follow_up_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'applied', ?, ?, ?)
        """,
        (
            job_id,
            company,
            title,
            recruiter_id,
            now,
            source,
            resume_version,
            cover_letter,
            follow_up,
            now,
            now,
        ),
    )
    repo._conn.commit()
    return int(cursor.lastrowid)


def update_stage(repo: JobRepository, application_id: int, stage: str, rejection_reason: str | None = None) -> None:
    now = utc_now()
    repo._conn.execute(
        """
        UPDATE applications
        SET stage = ?, rejection_reason = ?, updated_at = ?
        WHERE id = ?
        """,
        (stage, rejection_reason, now, application_id),
    )
    repo._conn.commit()


def list_applications(repo: JobRepository, limit: int = 20) -> list[ApplicationRecord]:
    rows = repo._conn.execute(
        """
        SELECT id, job_id, company, title, applied_at, source, resume_version, stage, follow_up_at
        FROM applications
        ORDER BY applied_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        ApplicationRecord(
            id=row["id"],
            job_id=row["job_id"],
            company=row["company"],
            title=row["title"],
            applied_at=row["applied_at"],
            source=row["source"],
            resume_version=row["resume_version"],
            stage=row["stage"],
            follow_up_at=row["follow_up_at"],
        )
        for row in rows
    ]


def due_followups(repo: JobRepository) -> list[ApplicationRecord]:
    rows = repo._conn.execute(
        """
        SELECT id, job_id, company, title, applied_at, source, resume_version, stage, follow_up_at
        FROM applications
        WHERE follow_up_at IS NOT NULL
          AND follow_up_at <= ?
          AND stage NOT IN ('rejected', 'offer', 'ghosted')
        ORDER BY follow_up_at ASC
        """,
        (utc_now(),),
    ).fetchall()
    return [
        ApplicationRecord(
            id=row["id"],
            job_id=row["job_id"],
            company=row["company"],
            title=row["title"],
            applied_at=row["applied_at"],
            source=row["source"],
            resume_version=row["resume_version"],
            stage=row["stage"],
            follow_up_at=row["follow_up_at"],
        )
        for row in rows
    ]
