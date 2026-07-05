from __future__ import annotations

from pathlib import Path

from ai.job_analyzer import JobAnalyzer
from ai.models import JobAnalysisRecord
from apply.matcher import MatchResult, match_job
from apply.pack import (
    activity_emoji,
    format_rules_pack_message,
    process_rules_actionable,
    save_pack,
)
from apply.resume_picker import portfolio_url, resume_url_for_variant
from database.repository import JobRecord, JobRepository


def priority_icon(priority: str, fit_score: int) -> str:
    if priority == "high" and fit_score >= 70:
        return "🔥"
    if priority == "medium":
        return "🟢"
    if priority == "low":
        return "🟡"
    return "📌"


def priority_label(priority: str) -> str:
    return priority.upper()


def format_gap_lines(analysis: JobAnalysisRecord) -> list[str]:
    lines: list[str] = []
    if analysis.output.must_have_gaps:
        lines.extend(f"• {gap}" for gap in analysis.output.must_have_gaps)
    if analysis.output.nice_to_have_gaps:
        lines.extend(f"• {gap} (nice-to-have)" for gap in analysis.output.nice_to_have_gaps)
    return lines


def format_intelligence_message(
    job: JobRecord,
    activity_type: str,
    match: MatchResult,
    analysis: JobAnalysisRecord,
    profile: dict,
) -> str:
    output = analysis.output
    icon = priority_icon(output.apply_priority, output.fit_score)
    warning = ""
    if not match.remote_ok:
        warning = "⚠️ Remote preference mismatch\n"
    if output.location_compatibility == "incompatible":
        warning += "⚠️ Location likely incompatible\n"

    strong_lines = "\n".join(f"• {item}" for item in output.strong_matches) or "• —"
    gap_lines = "\n".join(format_gap_lines(analysis)) or "• —"
    risk_lines = "\n".join(f"• {risk}" for risk in output.risk_factors) or "• —"

    reopened_note = (
        "\n🔄 Hiring likely restarted — worth reapplying"
        if activity_type == "reopened"
        else ""
    )

    cv_url = resume_url_for_variant(output.recommended_resume, profile)

    return f"""{activity_emoji(activity_type)} {icon} {output.fit_score} {priority_label(output.apply_priority)} · {job.title}
{job.company} · {output.employment_type} · {output.role_type}

Strong
{strong_lines}

Gaps
{gap_lines}

Risks
{risk_lines}
{warning}
CV: {output.recommended_resume} ({cv_url})
Why: {output.reason}

Portfolio: {portfolio_url(profile)}
Apply: {job.url}{reopened_note}"""


def should_notify(analysis: JobAnalysisRecord, profile: dict) -> bool:
    threshold = int(profile.get("match_threshold", 60))
    if analysis.output.apply_priority == "skip":
        return False
    if analysis.output.apply_priority == "low":
        return False
    return analysis.output.fit_score >= threshold


def process_actionable_job(
    repo: JobRepository,
    job: JobRecord,
    activity_type: str,
    profile: dict,
    detected_at: str,
    base_dir: Path | None = None,
) -> bool:
    root = base_dir or Path.cwd()
    match = match_job(job, profile=profile)
    prefilter_threshold = int(profile.get("prefilter_threshold", 45))

    if match.score < prefilter_threshold:
        return False

    if activity_type == "new" and repo.was_notified_for_role(job.company, job.title, "new"):
        return False

    analyzer = JobAnalyzer(base_dir=root)
    if not analyzer.enabled():
        return process_rules_actionable(repo, job, activity_type, profile, detected_at, match)

    analysis = analyzer.analyze_job(repo, job, match, profile=profile)
    if analysis is None or not should_notify(analysis, profile):
        return False

    message = format_intelligence_message(job, activity_type, match, analysis, profile)
    return save_pack(
        repo,
        job,
        activity_type,
        detected_at,
        message,
        profile,
        match_score=analysis.output.fit_score,
        match_strong=analysis.output.strong_matches,
        match_missing=analysis.output.must_have_gaps + analysis.output.nice_to_have_gaps,
        resume_version=analysis.output.recommended_resume,
        cover_letter="",
        job_analysis_id=analysis.id,
    )
