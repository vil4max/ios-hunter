from __future__ import annotations

import hashlib
from pathlib import Path

from database.repository import JobRecord

_PROFILE_FILES = (
    "config/profile.yaml",
    "config/career_facts.yaml",
    "config/skills.yaml",
)


def job_content_hash(job: JobRecord) -> str:
    raw = "|".join(
        [
            job.title.strip().lower(),
            (job.remote or "").strip().lower(),
            (job.description or "").strip(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def candidate_profile_hash(base_dir: Path) -> str:
    parts: list[str] = []
    for relative in _PROFILE_FILES:
        path = base_dir / relative
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    return hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()
