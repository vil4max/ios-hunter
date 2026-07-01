from __future__ import annotations

from database.repository import JobRepository


def render_crm_stats(repo: JobRepository) -> str:
    total = repo._conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    if total == 0:
        return "# CRM Stats\n\nNo applications logged yet."

    by_source = repo._conn.execute(
        """
        SELECT source, COUNT(*) AS cnt
        FROM applications GROUP BY source ORDER BY cnt DESC
        """
    ).fetchall()
    by_resume = repo._conn.execute(
        """
        SELECT COALESCE(resume_version, 'unknown') AS resume_version, COUNT(*) AS cnt
        FROM applications GROUP BY resume_version ORDER BY cnt DESC
        """
    ).fetchall()
    by_stage = repo._conn.execute(
        """
        SELECT stage, COUNT(*) AS cnt
        FROM applications GROUP BY stage ORDER BY cnt DESC
        """
    ).fetchall()

    lines = [
        "# CRM Stats",
        "",
        f"Total applications: {total}",
        "",
        "## By source",
        "",
    ]
    for row in by_source:
        lines.append(f"- {row['source']}: {row['cnt']}")

    lines.extend(["", "## By resume version", ""])
    for row in by_resume:
        lines.append(f"- {row['resume_version']}: {row['cnt']}")

    lines.extend(["", "## By stage", ""])
    for row in by_stage:
        lines.append(f"- {row['stage']}: {row['cnt']}")

    return "\n".join(lines) + "\n"
