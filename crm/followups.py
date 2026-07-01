from __future__ import annotations

from database.repository import JobRepository


def render_followup_digest(repo: JobRepository) -> str:
    rows = repo._conn.execute(
        """
        SELECT company, title, stage, follow_up_at
        FROM applications
        WHERE follow_up_at IS NOT NULL
          AND follow_up_at <= datetime('now')
          AND stage NOT IN ('rejected', 'offer', 'ghosted')
        ORDER BY follow_up_at ASC
        """
    ).fetchall()

    if not rows:
        return ""

    lines = ["CRM Follow-ups", "", f"{len(rows)} application(s) need follow-up:", ""]
    for row in rows:
        lines.append(f"• {row['company']} — {row['title']} ({row['stage']})")
    return "\n".join(lines)


def send_followup_reminders(repo: JobRepository) -> int:
    from integrations.telegram import send_message

    digest = render_followup_digest(repo)
    if not digest:
        return 0
    send_message(digest)
    return digest.count("• ")
