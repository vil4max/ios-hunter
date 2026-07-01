from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class JobRecord:
    id: str
    company: str
    title: str
    location: str | None
    remote: str | None
    url: str
    source: str
    published_at: str | None
    updated_at: str
    first_seen: str
    last_seen: str
    status: str
    description: str | None
    hash: str


class JobRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def _migrate(self) -> None:
        schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
        self._conn.executescript(schema)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def get_job_by_hash(self, job_hash: str) -> JobRecord | None:
        row = self._conn.execute("SELECT * FROM jobs WHERE hash = ?", (job_hash,)).fetchone()
        return self._row_to_job(row) if row else None

    def get_job_by_id(self, job_id: str) -> JobRecord | None:
        row = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_open_jobs(self) -> list[JobRecord]:
        rows = self._conn.execute("SELECT * FROM jobs WHERE status = 'open'").fetchall()
        return [self._row_to_job(row) for row in rows]

    def upsert_job(self, job: JobRecord) -> None:
        self._conn.execute(
            """
            INSERT INTO companies (name) VALUES (?)
            ON CONFLICT(name) DO NOTHING
            """,
            (job.company,),
        )
        company_id = self._conn.execute(
            "SELECT id FROM companies WHERE name = ?", (job.company,)
        ).fetchone()[0]

        self._conn.execute(
            """
            INSERT INTO jobs (
                id, company_id, company, title, location, remote, url, source,
                published_at, updated_at, first_seen, last_seen, status, description, hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                location = excluded.location,
                remote = excluded.remote,
                url = excluded.url,
                source = excluded.source,
                published_at = excluded.published_at,
                updated_at = excluded.updated_at,
                last_seen = excluded.last_seen,
                status = excluded.status,
                description = excluded.description
            """,
            (
                job.id,
                company_id,
                job.company,
                job.title,
                job.location,
                job.remote,
                job.url,
                job.source,
                job.published_at,
                job.updated_at,
                job.first_seen,
                job.last_seen,
                job.status,
                job.description,
                job.hash,
            ),
        )
        self._conn.commit()

    def mark_closed(self, job_id: str, when: str | None = None) -> None:
        when = when or utc_now()
        self._conn.execute(
            "UPDATE jobs SET status = 'closed', updated_at = ?, last_seen = ? WHERE id = ?",
            (when, when, job_id),
        )
        self._conn.commit()

    def add_history(
        self,
        job_id: str,
        change_type: str,
        old_value: str | None = None,
        new_value: str | None = None,
        diff: str | None = None,
        when: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO history (job_id, date, change_type, old_value, new_value, diff)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (job_id, when or utc_now(), change_type, old_value, new_value, diff),
        )
        self._conn.commit()

    def add_run_activity(
        self,
        run_id: int,
        job_id: str,
        activity_type: str,
        company: str,
        title: str,
        url: str | None,
        change_summary: str | None = None,
        diff: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO run_activity (
                run_id, job_id, activity_type, company, title, url, change_summary, diff, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                job_id,
                activity_type,
                company,
                title,
                url,
                change_summary,
                diff,
                utc_now(),
            ),
        )
        self._conn.commit()

    def start_run_metrics(self, started_at: str) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO run_metrics (started_at, finished_at, runtime_seconds)
            VALUES (?, ?, 0)
            """,
            (started_at, started_at),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def finish_run_metrics(self, run_id: int, metrics: dict[str, Any]) -> None:
        self._conn.execute(
            """
            UPDATE run_metrics SET
                finished_at = ?,
                runtime_seconds = ?,
                sources_total = ?,
                sources_healthy = ?,
                sources_failed = ?,
                new_jobs = ?,
                updated_jobs = ?,
                closed_jobs = ?,
                reopened_jobs = ?,
                actionable_jobs = ?,
                duplicates_removed = ?,
                quality_warnings = ?
            WHERE id = ?
            """,
            (
                metrics["finished_at"],
                metrics["runtime_seconds"],
                metrics.get("sources_total", 0),
                metrics.get("sources_healthy", 0),
                metrics.get("sources_failed", 0),
                metrics.get("new_jobs", 0),
                metrics.get("updated_jobs", 0),
                metrics.get("closed_jobs", 0),
                metrics.get("reopened_jobs", 0),
                metrics.get("actionable_jobs", 0),
                metrics.get("duplicates_removed", 0),
                metrics.get("quality_warnings", 0),
                run_id,
            ),
        )
        self._conn.commit()

    def upsert_source_health(
        self,
        source_id: str,
        source_name: str,
        source_url: str | None,
        status: str,
        error: str | None,
        response_ms: int | None,
        jobs_count: int,
    ) -> None:
        now = utc_now()
        row = self._conn.execute(
            """
            SELECT consecutive_failures, avg_jobs_count, avg_response_ms,
                   last_success_at, last_failure_at
            FROM source_health WHERE source_id = ?
            """,
            (source_id,),
        ).fetchone()

        if row:
            consecutive = 0 if status == "healthy" else int(row["consecutive_failures"]) + 1
            prev_avg_jobs = row["avg_jobs_count"] or 0.0
            prev_avg_ms = row["avg_response_ms"] or (response_ms or 0)
            avg_jobs = (prev_avg_jobs * 0.8) + (jobs_count * 0.2)
            avg_ms = int((prev_avg_ms * 0.8) + ((response_ms or prev_avg_ms) * 0.2))
            last_success = now if status == "healthy" else row["last_success_at"]
            last_failure = now if status != "healthy" else row["last_failure_at"]
        else:
            consecutive = 0 if status == "healthy" else 1
            avg_jobs = float(jobs_count)
            avg_ms = response_ms or 0
            last_success = now if status == "healthy" else None
            last_failure = now if status != "healthy" else None

        self._conn.execute(
            """
            INSERT INTO source_health (
                source_id, source_name, source_url, status, last_success_at, last_failure_at,
                last_error, consecutive_failures, avg_response_ms, avg_jobs_count, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                source_name = excluded.source_name,
                source_url = excluded.source_url,
                status = excluded.status,
                last_success_at = excluded.last_success_at,
                last_failure_at = excluded.last_failure_at,
                last_error = excluded.last_error,
                consecutive_failures = excluded.consecutive_failures,
                avg_response_ms = excluded.avg_response_ms,
                avg_jobs_count = excluded.avg_jobs_count,
                updated_at = excluded.updated_at
            """,
            (
                source_id,
                source_name,
                source_url,
                status,
                last_success,
                last_failure,
                error,
                consecutive,
                avg_ms,
                avg_jobs,
                now,
            ),
        )
        self._conn.commit()

    def save_application_pack(
        self,
        job_id: str,
        activity_type: str,
        match_score: int,
        match_strong: list[str],
        match_missing: list[str],
        resume_version: str,
        cover_letter: str,
        detected_at: str,
        pack_ready_at: str,
        notified_at: str | None = None,
    ) -> None:
        elapsed = (
            datetime.fromisoformat(pack_ready_at) - datetime.fromisoformat(detected_at)
        ).total_seconds()
        self._conn.execute(
            """
            INSERT INTO application_packs (
                job_id, activity_type, match_score, match_strong, match_missing,
                resume_version, cover_letter, detected_at, pack_ready_at,
                time_to_ready_seconds, notified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                activity_type,
                match_score,
                json.dumps(match_strong),
                json.dumps(match_missing),
                resume_version,
                cover_letter,
                detected_at,
                pack_ready_at,
                elapsed,
                notified_at,
            ),
        )
        self._conn.commit()

    def export_jobs_json(self, output_path: str | Path) -> None:
        rows = self._conn.execute(
            "SELECT company, title, location, remote, url, source, status, first_seen, last_seen FROM jobs WHERE status = 'open'"
        ).fetchall()
        payload = [dict(row) for row in rows]
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            id=row["id"],
            company=row["company"],
            title=row["title"],
            location=row["location"],
            remote=row["remote"],
            url=row["url"],
            source=row["source"],
            published_at=row["published_at"],
            updated_at=row["updated_at"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            status=row["status"],
            description=row["description"],
            hash=row["hash"],
        )
