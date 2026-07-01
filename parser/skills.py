from __future__ import annotations

from pathlib import Path

import yaml

from database.repository import JobRepository, utc_now


def load_skills(config_path: str | Path = "config/skills.yaml") -> dict[str, list[str]]:
    data = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    return {str(k): [str(v).lower() for v in values] for k, values in data.items()}


def extract_skills(text: str, skills_map: dict[str, list[str]]) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for skill, keywords in skills_map.items():
        if any(keyword in lowered for keyword in keywords):
            found.append(skill)
    return found


def sync_job_skills(repo: JobRepository, job_id: str, text: str, skills_map: dict[str, list[str]]) -> None:
    detected = extract_skills(text, skills_map)
    now = utc_now()
    for skill in detected:
        repo._conn.execute(
            """
            INSERT INTO skills (job_id, skill, detected_at)
            VALUES (?, ?, ?)
            ON CONFLICT(job_id, skill) DO NOTHING
            """,
            (job_id, skill, now),
        )
    repo._conn.commit()
