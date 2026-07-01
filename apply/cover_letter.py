from __future__ import annotations

from pathlib import Path

from apply.matcher import MatchResult, load_profile
from database.repository import JobRecord


def render_cover_letter(job: JobRecord, match: MatchResult, profile: dict | None = None) -> str:
    profile = profile or load_profile()
    template_path = Path("config/cover_letter_template.md")
    template = template_path.read_text(encoding="utf-8")

    strong = ", ".join(match.strong) if match.strong else "iOS development"
    focus_area = match.resume_version.replace("_", " ")
    highlight = (
        f"I have hands-on experience with {strong}, and I'm looking for remote roles "
        f"around ${profile.get('salary', {}).get('target_usd', 5000)} net."
    )

    return template.format(
        name=profile.get("name", "iOS Developer"),
        company=job.company,
        title=job.title,
        strong_skills=strong,
        focus_area=focus_area,
        highlight=highlight,
    ).strip()
