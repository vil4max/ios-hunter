from __future__ import annotations

from pathlib import Path

from apply.cover_letter import render_cover_letter
from apply.matcher import MatchResult, match_job
from apply.resume_picker import portfolio_url, resume_url, resume_url_for_variant
from database.repository import JobRecord, JobRepository, utc_now
from integrations.telegram import send_message

_REPO_ROOT = Path(__file__).resolve().parents[1]


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


def format_rules_pack_message(job: JobRecord, activity_type: str, match: MatchResult, cover_letter: str) -> str:
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


format_pack_message = format_rules_pack_message


def save_pack(
    repo: JobRepository,
    job: JobRecord,
    activity_type: str,
    detected_at: str,
    message: str,
    profile: dict,
    match_score: int,
    match_strong: list[str],
    match_missing: list[str],
    resume_version: str,
    cover_letter: str,
    job_analysis_id: int | None = None,
) -> bool:
    pack_ready_at = utc_now()

    if profile.get("telegram", {}).get("enabled", True):
        send_message(message)

    repo.save_application_pack(
        job_id=job.id,
        activity_type=activity_type,
        match_score=match_score,
        match_strong=match_strong,
        match_missing=match_missing,
        resume_version=resume_version,
        cover_letter=cover_letter,
        detected_at=detected_at,
        pack_ready_at=pack_ready_at,
        notified_at=pack_ready_at,
        job_analysis_id=job_analysis_id,
    )
    return True


def process_rules_actionable(
    repo: JobRepository,
    job: JobRecord,
    activity_type: str,
    profile: dict,
    detected_at: str,
    match: MatchResult | None = None,
) -> bool:
    threshold = int(profile.get("match_threshold", 60))
    match = match or match_job(job, profile=profile)
    cover_letter = render_cover_letter(job, match, profile=profile)

    if match.score < threshold:
        return False

    if activity_type == "new" and repo.was_notified_for_role(job.company, job.title, "new"):
        return False

    message = format_rules_pack_message(job, activity_type, match, cover_letter)
    return save_pack(
        repo,
        job,
        activity_type,
        detected_at,
        message,
        profile,
        match_score=match.score,
        match_strong=match.strong,
        match_missing=match.missing,
        resume_version=match.resume_version,
        cover_letter=cover_letter,
    )


def process_actionable(
    repo: JobRepository,
    job: JobRecord,
    activity_type: str,
    profile: dict,
    detected_at: str,
) -> bool:
    from apply.intelligence import process_actionable_job

    return process_actionable_job(
        repo, job, activity_type, profile, detected_at, base_dir=_REPO_ROOT
    )
