from __future__ import annotations

import json
import sqlite3
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from database.paths import resolve_db_path
from parser.normalize import canonicalize_url
from parser.normalize import role_key

_SCHEMA_SQL = (Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8")


@dataclass
class SourceHealthUpdate:
    consecutive: int
    avg_jobs: float
    avg_ms: int
    last_success: str | None
    last_failure: str | None


def _compute_source_health_update(
    row: sqlite3.Row | None,
    status: str,
    response_ms: int | None,
    jobs_count: int,
    now: str,
) -> SourceHealthUpdate:
    if row:
        consecutive = 0 if status == "healthy" else int(row["consecutive_failures"]) + 1
        prev_avg_jobs = row["avg_jobs_count"] or 0.0
        prev_avg_ms = row["avg_response_ms"] or (response_ms or 0)
        avg_jobs = (prev_avg_jobs * 0.8) + (jobs_count * 0.2)
        avg_ms = int((prev_avg_ms * 0.8) + ((response_ms or prev_avg_ms) * 0.2))
        last_success = now if status == "healthy" else row["last_success_at"]
        last_failure = now if status != "healthy" else row["last_failure_at"]
        return SourceHealthUpdate(consecutive, avg_jobs, avg_ms, last_success, last_failure)

    return SourceHealthUpdate(
        consecutive=0 if status == "healthy" else 1,
        avg_jobs=float(jobs_count),
        avg_ms=response_ms or 0,
        last_success=now if status == "healthy" else None,
        last_failure=now if status != "healthy" else None,
    )


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
    canonical_url: str
    source: str
    source_job_id: str | None
    identity_strategy: str
    identity_key: str
    published_at: str | None
    updated_at: str
    first_seen: str
    last_seen: str
    status: str
    description: str | None
    hash: str


@dataclass
class StoredJobAnalysis:
    id: int
    job_id: str
    fit_score: int
    apply_priority: str
    recommended_resume: str | None
    prefilter_score: int | None
    analysis_json: str
    job_content_hash: str
    candidate_profile_hash: str
    prompt_version: str
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    analyzed_at: str


class JobRepository:
    def __init__(self, db_path: str | Path, base_dir: Path | None = None) -> None:
        self.db_path = resolve_db_path(db_path, base_dir=base_dir)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def _repair_identity_key_uniqueness(self) -> None:
        self._conn.execute("UPDATE jobs SET identity_key = id WHERE identity_key IS NULL OR identity_key = ''")
        self._conn.execute(
            """
            WITH dupes AS (
                SELECT identity_key
                FROM jobs
                WHERE identity_key != ''
                GROUP BY identity_key
                HAVING COUNT(*) > 1
            )
            UPDATE jobs
            SET identity_key = id
            WHERE identity_key IN (SELECT identity_key FROM dupes)
            """
        )

    def _migrate(self) -> None:
        self._conn.executescript(_SCHEMA_SQL)
        job_columns = {row[1] for row in self._conn.execute("PRAGMA table_info(jobs)")}
        if "canonical_url" not in job_columns:
            self._conn.execute("ALTER TABLE jobs ADD COLUMN canonical_url TEXT NOT NULL DEFAULT ''")
        if "source_job_id" not in job_columns:
            self._conn.execute("ALTER TABLE jobs ADD COLUMN source_job_id TEXT")
        if "identity_strategy" not in job_columns:
            self._conn.execute("ALTER TABLE jobs ADD COLUMN identity_strategy TEXT NOT NULL DEFAULT 'legacy'")
        if "identity_key" not in job_columns:
            self._conn.execute("ALTER TABLE jobs ADD COLUMN identity_key TEXT NOT NULL DEFAULT ''")

        pack_columns = {row[1] for row in self._conn.execute("PRAGMA table_info(application_packs)")}
        if "job_analysis_id" not in pack_columns:
            self._conn.execute(
                "ALTER TABLE application_packs ADD COLUMN job_analysis_id INTEGER REFERENCES job_analysis(id)"
            )
        self._migrate_job_identity()
        self._repair_identity_key_uniqueness()
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_identity_key ON jobs(identity_key)"
        )
        self._conn.commit()

    def _migrate_job_identity(self) -> None:
        rows = self._conn.execute(
            "SELECT id, company, url, canonical_url, identity_key FROM jobs"
        ).fetchall()
        if not rows:
            return

        updates: list[tuple[str, str, str]] = []
        for row in rows:
            current_id = str(row["id"])
            company = str(row["company"] or "")
            url = str(row["url"] or "")
            canon = str(row["canonical_url"] or "") or canonicalize_url(url)
            desired_key = str(row["identity_key"] or "").strip()
            if not desired_key:
                desired_key = (
                    hashlib.sha256(f"url|{company.strip().lower()}|{canon}".encode("utf-8")).hexdigest()
                    if canon
                    else current_id
                )
            updates.append((canon, desired_key, current_id))

        self._conn.executemany(
            "UPDATE jobs SET canonical_url = ?, identity_key = ? WHERE id = ?",
            updates,
        )

    def close(self) -> None:
        self._conn.close()

    def get_job_by_hash(self, job_hash: str) -> JobRecord | None:
        row = self._conn.execute("SELECT * FROM jobs WHERE hash = ?", (job_hash,)).fetchone()
        return self._row_to_job(row) if row else None

    def get_job_by_identity_key(self, identity_key: str) -> JobRecord | None:
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE id = ? OR identity_key = ? LIMIT 1",
            (identity_key, identity_key),
        ).fetchone()
        return self._row_to_job(row) if row else None

    def get_job_by_company_title(self, company: str, title: str) -> JobRecord | None:
        target = role_key(company, title)
        rows = self._conn.execute(
            "SELECT * FROM jobs WHERE lower(company) = ?",
            (target[0],),
        ).fetchall()
        for row in rows:
            if role_key(row["company"], row["title"]) == target:
                return self._row_to_job(row)
        return None

    def was_notified_for_role(self, company: str, title: str, activity_type: str = "new") -> bool:
        target = role_key(company, title)
        rows = self._conn.execute(
            """
            SELECT j.company, j.title
            FROM application_packs ap
            JOIN jobs j ON j.id = ap.job_id
            WHERE ap.activity_type = ?
            """,
            (activity_type,),
        ).fetchall()
        for row in rows:
            if role_key(row["company"], row["title"]) == target:
                return True
        return False

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
                id, company_id, company, title, location, remote, url, canonical_url, source,
                source_job_id, identity_strategy, identity_key,
                published_at, updated_at, first_seen, last_seen, status, description, hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                location = excluded.location,
                remote = excluded.remote,
                url = excluded.url,
                canonical_url = excluded.canonical_url,
                source = excluded.source,
                source_job_id = excluded.source_job_id,
                identity_strategy = excluded.identity_strategy,
                identity_key = excluded.identity_key,
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
                job.canonical_url,
                job.source,
                job.source_job_id,
                job.identity_strategy,
                job.identity_key,
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
            "UPDATE jobs SET status = 'closed', updated_at = ?, last_seen = ?, description = NULL WHERE id = ?",
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

        metrics = _compute_source_health_update(row, status, response_ms, jobs_count, now)

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
                metrics.last_success,
                metrics.last_failure,
                error,
                metrics.consecutive,
                metrics.avg_ms,
                metrics.avg_jobs,
                now,
            ),
        )
        self._conn.commit()

    def get_cached_job_analysis(
        self,
        job_id: str,
        job_content_hash: str,
        candidate_profile_hash: str,
        prompt_version: str,
        model: str,
    ) -> "JobAnalysisRecord | None":
        from ai.models import JobAnalysisOutput, JobAnalysisRecord

        row = self._conn.execute(
            """
            SELECT * FROM job_analysis
            WHERE job_id = ?
              AND job_content_hash = ?
              AND candidate_profile_hash = ?
              AND prompt_version = ?
              AND model = ?
            ORDER BY analyzed_at DESC
            LIMIT 1
            """,
            (job_id, job_content_hash, candidate_profile_hash, prompt_version, model),
        ).fetchone()
        if row is None:
            return None
        stored = self._row_to_stored_analysis(row)
        return JobAnalysisRecord(
            id=stored.id,
            job_id=stored.job_id,
            output=JobAnalysisOutput.model_validate_json(stored.analysis_json),
            prefilter_score=stored.prefilter_score or 0,
            job_content_hash=stored.job_content_hash,
            candidate_profile_hash=stored.candidate_profile_hash,
            prompt_version=stored.prompt_version,
            provider=stored.provider,
            model=stored.model,
            input_tokens=stored.input_tokens,
            output_tokens=stored.output_tokens,
            analyzed_at=stored.analyzed_at,
        )

    def save_job_analysis(self, record: "JobAnalysisRecord") -> "JobAnalysisRecord":
        from ai.models import JobAnalysisRecord

        payload = record.output.model_dump_json()
        cursor = self._conn.execute(
            """
            INSERT INTO job_analysis (
                job_id, fit_score, apply_priority, recommended_resume, prefilter_score,
                analysis_json, job_content_hash, candidate_profile_hash,
                prompt_version, provider, model, input_tokens, output_tokens, analyzed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id, job_content_hash, candidate_profile_hash, prompt_version, model)
            DO UPDATE SET
                fit_score = excluded.fit_score,
                apply_priority = excluded.apply_priority,
                recommended_resume = excluded.recommended_resume,
                prefilter_score = excluded.prefilter_score,
                analysis_json = excluded.analysis_json,
                provider = excluded.provider,
                input_tokens = excluded.input_tokens,
                output_tokens = excluded.output_tokens,
                analyzed_at = excluded.analyzed_at
            """,
            (
                record.job_id,
                record.output.fit_score,
                record.output.apply_priority,
                record.output.recommended_resume,
                record.prefilter_score,
                payload,
                record.job_content_hash,
                record.candidate_profile_hash,
                record.prompt_version,
                record.provider,
                record.model,
                record.input_tokens,
                record.output_tokens,
                record.analyzed_at,
            ),
        )
        self._conn.commit()
        analysis_id = int(cursor.lastrowid)
        if analysis_id == 0:
            row = self._conn.execute(
                """
                SELECT id FROM job_analysis
                WHERE job_id = ?
                  AND job_content_hash = ?
                  AND candidate_profile_hash = ?
                  AND prompt_version = ?
                  AND model = ?
                """,
                (
                    record.job_id,
                    record.job_content_hash,
                    record.candidate_profile_hash,
                    record.prompt_version,
                    record.model,
                ),
            ).fetchone()
            analysis_id = int(row["id"])
        return JobAnalysisRecord(
            id=analysis_id,
            job_id=record.job_id,
            output=record.output,
            prefilter_score=record.prefilter_score,
            job_content_hash=record.job_content_hash,
            candidate_profile_hash=record.candidate_profile_hash,
            prompt_version=record.prompt_version,
            provider=record.provider,
            model=record.model,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            analyzed_at=record.analyzed_at,
        )

    @staticmethod
    def _row_to_stored_analysis(row: sqlite3.Row) -> StoredJobAnalysis:
        return StoredJobAnalysis(
            id=int(row["id"]),
            job_id=row["job_id"],
            fit_score=int(row["fit_score"]),
            apply_priority=row["apply_priority"],
            recommended_resume=row["recommended_resume"],
            prefilter_score=row["prefilter_score"],
            analysis_json=row["analysis_json"],
            job_content_hash=row["job_content_hash"],
            candidate_profile_hash=row["candidate_profile_hash"],
            prompt_version=row["prompt_version"],
            provider=row["provider"],
            model=row["model"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            analyzed_at=row["analyzed_at"],
        )

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
        job_analysis_id: int | None = None,
    ) -> None:
        elapsed = (
            datetime.fromisoformat(pack_ready_at) - datetime.fromisoformat(detected_at)
        ).total_seconds()
        self._conn.execute(
            """
            INSERT INTO application_packs (
                job_id, activity_type, match_score, match_strong, match_missing,
                resume_version, cover_letter, job_analysis_id, detected_at, pack_ready_at,
                time_to_ready_seconds, notified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                activity_type,
                match_score,
                json.dumps(match_strong),
                json.dumps(match_missing),
                resume_version,
                cover_letter,
                job_analysis_id,
                detected_at,
                pack_ready_at,
                elapsed,
                notified_at,
            ),
        )
        self._conn.commit()

    def record_company_watch_alert(self, company: str, when: str | None = None) -> None:
        self._conn.execute(
            """
            INSERT INTO watch_alerts (company, alerted_at) VALUES (?, ?)
            ON CONFLICT(company) DO UPDATE SET alerted_at = excluded.alerted_at
            """,
            (company, when or utc_now()),
        )
        self._conn.commit()

    def reserve_notification_event(
        self,
        *,
        event_key: str,
        job_id: str,
        event_type: str,
        content_hash: str,
        now: str | None = None,
        lock_ttl_minutes: int = 10,
    ) -> bool:
        now = now or utc_now()
        cutoff = (
            datetime.fromisoformat(now) - timedelta(minutes=lock_ttl_minutes)
        ).replace(microsecond=0).isoformat()
        self._conn.execute("BEGIN IMMEDIATE")
        self._conn.execute(
            """
            INSERT INTO notification_events (event_key, job_id, event_type, content_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(event_key) DO NOTHING
            """,
            (event_key, job_id, event_type, content_hash, now),
        )
        row = self._conn.execute(
            "SELECT locked_at, sent_at FROM notification_events WHERE event_key = ?",
            (event_key,),
        ).fetchone()
        if row is None:
            self._conn.commit()
            return False
        if row["sent_at"]:
            self._conn.commit()
            return False

        cursor = self._conn.execute(
            """
            UPDATE notification_events
            SET locked_at = ?
            WHERE event_key = ?
              AND sent_at IS NULL
              AND (locked_at IS NULL OR locked_at < ?)
            """,
            (now, event_key, cutoff),
        )
        self._conn.commit()
        return cursor.rowcount == 1

    def mark_notification_event_sent(self, *, event_key: str, now: str | None = None) -> None:
        now = now or utc_now()
        self._conn.execute(
            "UPDATE notification_events SET sent_at = ? WHERE event_key = ?",
            (now, event_key),
        )
        self._conn.commit()

    def company_watch_alerted_recently(self, company: str, days: int = 7) -> bool:
        row = self._conn.execute(
            """
            SELECT 1 FROM watch_alerts
            WHERE company = ? AND alerted_at >= datetime('now', ?)
            LIMIT 1
            """,
            (company, f"-{days} days"),
        ).fetchone()
        return row is not None

    def export_jobs_json(self, output_path: str | Path) -> None:
        rows = self._conn.execute(
            "SELECT company, title, location, remote, url, source, status, first_seen, last_seen FROM jobs WHERE status = 'open'"
        ).fetchall()
        payload = [dict(row) for row in rows]
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def prune_jobs_older_than(self, days: int = 45) -> int:
        """
        Prune old jobs and related rows to keep the SQLite cache bounded.

        Notes:
        - We prune by `last_seen` (not `published_at`) because many sources do not expose publish dates.
        - We do not delete jobs referenced by CRM `applications` to avoid breaking that workflow.
        """
        job_rows = self._conn.execute(
            """
            SELECT id FROM jobs
            WHERE last_seen < datetime('now', ?)
              AND id NOT IN (SELECT job_id FROM applications WHERE job_id IS NOT NULL)
            """,
            (f"-{days} days",),
        ).fetchall()
        job_ids = [row["id"] for row in job_rows]
        if not job_ids:
            return 0

        cutoff = f"-{days} days"
        stale_job_ids = """
            job_id IN (
                SELECT id FROM jobs
                WHERE last_seen < datetime('now', ?)
                  AND id NOT IN (SELECT job_id FROM applications WHERE job_id IS NOT NULL)
            )
        """
        self._conn.execute(
            f"DELETE FROM skills WHERE {stale_job_ids}",
            (cutoff,),
        )
        self._conn.execute(
            f"DELETE FROM job_sources WHERE {stale_job_ids}",
            (cutoff,),
        )
        self._conn.execute(
            f"DELETE FROM history WHERE {stale_job_ids}",
            (cutoff,),
        )
        self._conn.execute(
            f"DELETE FROM run_activity WHERE {stale_job_ids}",
            (cutoff,),
        )
        self._conn.execute(
            f"DELETE FROM application_packs WHERE {stale_job_ids}",
            (cutoff,),
        )
        self._conn.execute(
            f"DELETE FROM job_analysis WHERE {stale_job_ids}",
            (cutoff,),
        )
        self._conn.execute(
            """
            DELETE FROM jobs
            WHERE last_seen < datetime('now', ?)
              AND id NOT IN (SELECT job_id FROM applications WHERE job_id IS NOT NULL)
            """,
            (cutoff,),
        )
        self._conn.commit()
        return len(job_ids)

    def history_change_counts(self, days: int = 7) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT change_type, COUNT(*) AS count
            FROM history
            WHERE date >= datetime('now', ?)
            GROUP BY change_type
            """,
            (f"-{days} days",),
        ).fetchall()
        return [dict(row) for row in rows]

    def export_history_json(self, output_path: str | Path, days: int = 30) -> None:
        rows = self._conn.execute(
            """
            SELECT job_id, date AS changed_at, change_type AS field, old_value, new_value, diff
            FROM history
            WHERE date >= datetime('now', ?)
            ORDER BY date DESC
            """,
            (f"-{days} days",),
        ).fetchall()
        payload = [dict(row) for row in rows]
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def weekly_activity_from_metrics(self) -> tuple[int, int, int, int] | None:
        row = self._conn.execute(
            """
            SELECT
                COALESCE(SUM(new_jobs), 0),
                COALESCE(SUM(closed_jobs), 0),
                COALESCE(SUM(reopened_jobs), 0),
                COALESCE(SUM(updated_jobs), 0)
            FROM run_metrics
            WHERE finished_at >= datetime('now', '-7 days')
            """
        ).fetchone()
        if not row:
            return None
        values = tuple(int(value) for value in row)
        if sum(values) == 0:
            return None
        return values

    def weekly_activity_from_history(self) -> tuple[int, int, int, int]:
        mapping = {
            "created": 0,
            "closed": 1,
            "reopened": 2,
            "description_changed": 3,
        }
        counts = [0, 0, 0, 0]
        rows = self.history_change_counts(days=7)
        for row in rows:
            change_type = row["change_type"]
            if change_type in mapping:
                counts[mapping[change_type]] += int(row["count"])
        return tuple(counts)

    def count_open_jobs(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM jobs WHERE status = 'open'"
        ).fetchone()
        return int(row["count"])

    def count_tracked_jobs(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS count FROM jobs").fetchone()
        return int(row["count"])

    def count_open_by_remote(self) -> dict[str, int]:
        rows = self._conn.execute(
            """
            SELECT COALESCE(remote, 'unknown') AS remote, COUNT(*) AS count
            FROM jobs WHERE status = 'open'
            GROUP BY COALESCE(remote, 'unknown')
            """
        ).fetchall()
        return {row["remote"]: int(row["count"]) for row in rows}

    def top_open_companies(self, limit: int = 10) -> list[tuple[str, int]]:
        rows = self._conn.execute(
            """
            SELECT company, COUNT(*) AS count
            FROM jobs WHERE status = 'open'
            GROUP BY company ORDER BY count DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [(row["company"], int(row["count"])) for row in rows]

    def company_lifetime_stats(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT
                company,
                SUM(CASE WHEN first_seen >= date('now', 'start of year') THEN 1 ELSE 0 END) AS jobs_this_year,
                SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_jobs,
                AVG(CASE WHEN status = 'closed' THEN julianday(last_seen) - julianday(first_seen) END) AS avg_lifetime_days
            FROM jobs
            GROUP BY company
            HAVING open_jobs > 0
            ORDER BY open_jobs DESC, jobs_this_year DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def recent_notable_changes(self, days: int = 7, limit: int = 10) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT h.change_type, h.date, j.company, j.title, j.url
            FROM history h
            JOIN jobs j ON j.id = h.job_id
            WHERE h.date >= datetime('now', ?)
              AND h.change_type IN ('reopened', 'closed', 'created')
            ORDER BY h.date DESC
            LIMIT ?
            """,
            (f"-{days} days", limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def recent_actionable_activity(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT j.company, j.title, j.url, ra.activity_type, ra.created_at
            FROM run_activity ra
            JOIN jobs j ON j.id = ra.job_id
            WHERE ra.activity_type IN ('new', 'updated', 'reopened')
            ORDER BY ra.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            id=row["id"],
            company=row["company"],
            title=row["title"],
            location=row["location"],
            remote=row["remote"],
            url=row["url"],
            canonical_url=row["canonical_url"],
            source=row["source"],
            source_job_id=row["source_job_id"],
            identity_strategy=row["identity_strategy"],
            identity_key=row["identity_key"],
            published_at=row["published_at"],
            updated_at=row["updated_at"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            status=row["status"],
            description=row["description"],
            hash=row["hash"],
        )
