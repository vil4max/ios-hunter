from __future__ import annotations

import json
from datetime import datetime, timezone

from database.repository import JobRepository, utc_now


def render_bar(count: int, max_count: int, width: int = 20) -> str:
    if max_count <= 0:
        return " " * width
    filled = max(1, int(round((count / max_count) * width))) if count > 0 else 0
    return "█" * filled


def upsert_current_month_snapshot(repo: JobRepository) -> None:
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    new_jobs = repo._conn.execute(
        """
        SELECT COUNT(*) FROM jobs
        WHERE strftime('%Y-%m', first_seen) = ?
        """,
        (period,),
    ).fetchone()[0]
    closed_jobs = repo._conn.execute(
        """
        SELECT COUNT(*) FROM history
        WHERE change_type = 'closed' AND strftime('%Y-%m', date) = ?
        """,
        (period,),
    ).fetchone()[0]
    active_jobs = repo._conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE status = 'open'"
    ).fetchone()[0]
    remote_count = repo._conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE status = 'open' AND remote = 'remote'"
    ).fetchone()[0]
    hybrid_count = repo._conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE status = 'open' AND remote = 'hybrid'"
    ).fetchone()[0]
    onsite_count = repo._conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE status = 'open' AND remote = 'onsite'"
    ).fetchone()[0]

    avg_lifetime = repo._conn.execute(
        """
        SELECT AVG(
            julianday(last_seen) - julianday(first_seen)
        ) FROM jobs WHERE status = 'closed'
        """
    ).fetchone()[0]

    top_rows = repo._conn.execute(
        """
        SELECT company, COUNT(*) AS cnt
        FROM jobs
        WHERE strftime('%Y-%m', first_seen) = ?
        GROUP BY company
        ORDER BY cnt DESC
        LIMIT 20
        """,
        (period,),
    ).fetchall()

    repo._conn.execute(
        """
        INSERT INTO market_snapshots (
            period, new_jobs, closed_jobs, active_jobs, remote_count, hybrid_count,
            onsite_count, avg_lifetime_days, new_companies, top_hirers_json,
            skill_trends_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, '{}', ?)
        ON CONFLICT(period) DO UPDATE SET
            new_jobs = excluded.new_jobs,
            closed_jobs = excluded.closed_jobs,
            active_jobs = excluded.active_jobs,
            remote_count = excluded.remote_count,
            hybrid_count = excluded.hybrid_count,
            onsite_count = excluded.onsite_count,
            avg_lifetime_days = excluded.avg_lifetime_days,
            top_hirers_json = excluded.top_hirers_json,
            created_at = excluded.created_at
        """,
        (
            period,
            int(new_jobs),
            int(closed_jobs),
            int(active_jobs),
            int(remote_count),
            int(hybrid_count),
            int(onsite_count),
            float(avg_lifetime or 0),
            json.dumps([{"company": row["company"], "jobs": row["cnt"]} for row in top_rows]),
            utc_now(),
        ),
    )
    repo._conn.commit()


def render_timeline_report(repo: JobRepository) -> str:
    rows = repo._conn.execute(
        """
        SELECT period, new_jobs FROM market_snapshots
        ORDER BY period DESC LIMIT 12
        """
    ).fetchall()
    if not rows:
        return "# Market Timeline\n\nCollecting data — timeline will appear after the first month."

    ordered = list(reversed(rows))
    max_count = max(int(row["new_jobs"]) for row in ordered) or 1
    lines = ["# Market Timeline", ""]
    for row in ordered:
        year, month = row["period"].split("-")
        month_name = datetime(int(year), int(month), 1).strftime("%B %Y")
        bar = render_bar(int(row["new_jobs"]), max_count)
        lines.append(f"{month_name}")
        lines.append(f"{bar} {row['new_jobs']} vacancies")
        lines.append("")
    return "\n".join(lines).strip()
