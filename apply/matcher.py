from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from database.repository import JobRecord


@dataclass
class MatchResult:
    score: int
    strong: list[str]
    missing: list[str]
    salary_usd: int | None
    salary_ok: bool
    remote_ok: bool
    resume_version: str


def load_skills(config_path: str | Path = "config/skills.yaml") -> dict[str, list[str]]:
    data = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    return {str(k): [str(v).lower() for v in values] for k, values in data.items()}


def load_profile(config_path: str | Path = "config/profile.yaml") -> dict:
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))


def user_skills(profile: dict) -> list[str]:
    return [str(skill) for skill in profile.get("skills", [])]


def extract_salary_usd(text: str) -> int | None:
    lowered = text.lower()
    patterns = [
        r"\$\s*(\d[\d,]*)\s*(?:k|000)?",
        r"(\d[\d,]*)\s*(?:usd|\$)",
        r"(\d[\d,]*)\s*(?:грн|uah)",
    ]
    values: list[int] = []
    for pattern in patterns:
        for match in re.finditer(pattern, lowered):
            raw = match.group(1).replace(",", "")
            try:
                value = int(raw)
            except ValueError:
                continue
            if "грн" in match.group(0) or "uah" in match.group(0):
                value = int(value / 41)
            elif value < 1000:
                value *= 1000
            values.append(value)
    return max(values) if values else None


def detect_skills(text: str, skills_map: dict[str, list[str]]) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for skill, keywords in skills_map.items():
        if any(keyword in lowered for keyword in keywords):
            found.append(skill)
    return found


def pick_resume_version(strong_overlap: list[str]) -> str:
    priority = [
        ("AI", "ai"),
        ("SDK", "sdk"),
        ("Product", "product"),
    ]
    overlap = {skill.lower() for skill in strong_overlap}
    for label, version in priority:
        if label.lower() in overlap:
            return version
    return "product"


def match_job(job: JobRecord, profile: dict | None = None, skills_map: dict[str, list[str]] | None = None) -> MatchResult:
    profile = profile or load_profile()
    skills_map = skills_map or load_skills()

    text = f"{job.title} {job.description or ''}"
    job_skills = set(detect_skills(text, skills_map))
    mine = set(user_skills(profile))
    priority = profile.get("skill_priority", list(mine))

    strong = [skill for skill in priority if skill in mine and skill in job_skills][:4]
    missing = [skill for skill in priority if skill in job_skills and skill not in mine][:3]

    score = 40
    score += min(len(strong) * 10, 40)
    if job.remote == "remote":
        score += 10
    elif job.remote == "hybrid":
        score += 5

    salary_min = int(profile.get("salary", {}).get("minimum_usd", 4500))
    salary_target = int(profile.get("salary", {}).get("target_usd", 6000))
    salary_usd = extract_salary_usd(text)
    salary_ok = True if salary_usd is None else salary_usd >= salary_min
    if salary_usd and salary_usd >= salary_target:
        score += 10
    elif salary_ok:
        score += 5
    if not salary_ok:
        score -= 25

    remote_pref = profile.get("remote_preference", "remote")
    remote_ok = job.remote in {remote_pref, "remote", "hybrid", "unknown"}
    if remote_pref == "remote" and job.remote == "onsite":
        score -= 15
        remote_ok = False

    resume_version = pick_resume_version(strong)
    score = max(0, min(100, score))

    return MatchResult(
        score=score,
        strong=strong,
        missing=missing,
        salary_usd=salary_usd,
        salary_ok=salary_ok,
        remote_ok=remote_ok,
        resume_version=resume_version,
    )
