from __future__ import annotations

from apply.cover_letter import render_cover_letter
from apply.matcher import MatchResult, match_job
from apply.resume_picker import portfolio_url, resume_url
from database.repository import JobRecord, JobRepository, utc_now
from integrations.telegram import send_message


def activity_emoji(activity_type: str) -> str:
    return {
        "new": "🟢 New",
        "updated": "✏️ Updated",
        "reopened": "🔄 Reopened",
    }.get(activity_type, "📌")


def build_application_pack(job: JobRecord, activity_type: str) -> tuple[MatchResult, str]:
    _ = activity_type
    match = match_job(job)
    letter = render_cover_letter(job, match)
    return match, letter


def format_pack_message(job: JobRecord, activity_type: str, match: MatchResult, cover_letter: str) -> str:
    warning = ""
    if not match.remote_ok:
        warning += "⚠️ Remote preference mismatch\n"

    reopened_note = (
        "\n🔄 Hiring likely restarted — worth reapplying"
        if activity_type == "reopened"
        else ""
    )

    return f"""{activity_emoji(activity_type)} — {job.company} — {job.title}
Match: {match.score}%

Strong: {", ".join(match.strong) or "—"}
Gap: {", ".join(match.missing) or "—"}
{warning}
Cover letter:
{cover_letter}

CV: {resume_url(match)}
Portfolio: {portfolio_url()}

Apply: {job.url}{reopened_note}"""


def process_actionable(
    repo: JobRepository,
    job: JobRecord,
    activity_type: str,
    profile: dict,
    detected_at: str,
) -> bool:
    threshold = int(profile.get("match_threshold", 60))
    match, cover_letter = build_application_pack(job, activity_type)

    if match.score < threshold:
        return False

    pack_ready_at = utc_now()
    message = format_pack_message(job, activity_type, match, cover_letter)

    if profile.get("telegram", {}).get("enabled", True):
        send_message(message)

    repo.save_application_pack(
        job_id=job.id,
        activity_type=activity_type,
        match_score=match.score,
        match_strong=match.strong,
        match_missing=match.missing,
        resume_version=match.resume_version,
        cover_letter=cover_letter,
        detected_at=detected_at,
        pack_ready_at=pack_ready_at,
        notified_at=pack_ready_at,
    )
    return True
