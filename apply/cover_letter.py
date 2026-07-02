from __future__ import annotations

from pathlib import Path

from apply.matcher import MatchResult, load_profile, user_skills
from database.repository import JobRecord


def render_cover_letter(job: JobRecord, match: MatchResult, profile: dict | None = None) -> str:
    profile = profile or load_profile()
    template_path = Path("config/cover_letter_template.md")
    template = template_path.read_text(encoding="utf-8")

    focus_labels = profile.get("resume_focus", {})
    focus_area = focus_labels.get(match.resume_version, "iOS product development")

    claimed = ", ".join(match.strong) if match.strong else ", ".join(user_skills(profile)[:4])
    highlight = (
        f"Recent work includes {focus_area}. "
        f"Relevant strengths for this role: {claimed}."
    )

    cover_letter_cfg = profile.get("cover_letter", {})
    if cover_letter_cfg.get("include_salary", False):
        highlight += " I'm targeting remote roles with market-competitive compensation."

    return template.format(
        name=profile.get("name", "Max Vilchevskiy"),
        company=job.company,
        title=job.title,
        experience_years=profile.get("experience_years", 12),
        focus_area=focus_area,
        highlight=highlight,
    ).strip()
