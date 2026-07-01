from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Vacancy:
    company: str
    title: str
    url: str
    source: str
    location: str | None = None
    remote: str | None = None
    published_at: datetime | None = None
    description: str | None = None
    hash: str = field(default="", init=False)

    def __post_init__(self) -> None:
        self.hash = compute_hash(self.company, self.title, self.location)


def compute_hash(company: str, title: str, location: str | None) -> str:
    raw = "|".join(
        [
            normalize_token(company),
            normalize_token(title),
            normalize_token(location or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_token(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def is_ios_job(title: str, description: str | None = None) -> bool:
    haystack = f"{title} {description or ''}".lower()
    return "ios" in haystack or "swift" in haystack


def infer_remote(title: str, location: str | None, description: str | None) -> str:
    text = f"{title} {location or ''} {description or ''}".lower()
    if any(word in text for word in ("remote", "remotely", "віддалено", "удаленно")):
        return "remote"
    if any(word in text for word in ("hybrid", "гібрид")):
        return "hybrid"
    if any(word in text for word in ("onsite", "office", "офіс", "офис")):
        return "onsite"
    return "unknown"


def normalize_raw(raw: dict[str, Any]) -> Vacancy | None:
    title = str(raw.get("title", "")).strip()
    company = str(raw.get("company", "")).strip()
    url = str(raw.get("url", "")).strip()
    if not title or not company or not url:
        return None

    description = raw.get("description")
    if description is not None:
        description = str(description).strip() or None

    if not is_ios_job(title, description):
        return None

    location = raw.get("location")
    location = str(location).strip() if location else None
    remote = raw.get("remote") or infer_remote(title, location, description)

    published_at = None
    if raw.get("published_at"):
        try:
            published_at = datetime.fromisoformat(str(raw["published_at"]).replace("Z", "+00:00"))
        except ValueError:
            published_at = None

    return Vacancy(
        company=company,
        title=title,
        url=url,
        source=str(raw.get("source", "company")),
        location=location,
        remote=str(remote),
        published_at=published_at,
        description=description,
    )


def normalize_many(raw_jobs: list[dict[str, Any]]) -> list[Vacancy]:
    vacancies: list[Vacancy] = []
    for raw in raw_jobs:
        vacancy = normalize_raw(raw)
        if vacancy:
            vacancies.append(vacancy)
    return vacancies
