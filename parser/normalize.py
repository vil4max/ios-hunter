from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


_TRACKING_QUERY_KEYS = {
    "ref",
    "source",
    "gh_src",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "utm_reader",
}


def canonicalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""

    split = urlsplit(raw)
    scheme = (split.scheme or "https").lower()
    host = (split.hostname or "").lower()
    netloc = host
    if split.port and ((scheme == "http" and split.port != 80) or (scheme == "https" and split.port != 443)):
        netloc = f"{host}:{split.port}"

    path = split.path or "/"
    if path != "/":
        path = path.rstrip("/")

    query_items: list[tuple[str, str]] = []
    for key, value in parse_qsl(split.query, keep_blank_values=True):
        lowered_key = key.lower()
        if lowered_key.startswith("utm_"):
            continue
        if lowered_key in _TRACKING_QUERY_KEYS:
            continue
        query_items.append((key, value))

    query_items.sort(key=lambda kv: (kv[0], kv[1]))
    query = urlencode(query_items, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def compute_identity_key(
    *,
    company: str,
    canonical_url: str,
    source: str,
    source_job_id: str | None,
) -> tuple[str, str]:
    normalized_company = normalize_token(company)
    normalized_source = normalize_token(source)
    if source_job_id:
        raw = f"provider|{normalized_company}|{normalized_source}|{source_job_id.strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest(), "source_job_id"
    if canonical_url:
        raw = f"url|{normalized_company}|{canonical_url}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest(), "canonical_url"
    raw = f"fallback|{normalized_company}|{normalize_token(canonical_url)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest(), "fallback"


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
    canonical_url: str = ""
    source_job_id: str | None = None
    identity_key: str = ""
    identity_strategy: str = ""
    hash: str = field(default="", init=False)

    def __post_init__(self) -> None:
        self.canonical_url = self.canonical_url or canonicalize_url(self.url)
        if not self.identity_key:
            self.identity_key, self.identity_strategy = compute_identity_key(
                company=self.company,
                canonical_url=self.canonical_url,
                source=self.source,
                source_job_id=self.source_job_id,
            )
        self.hash = self.identity_key or compute_hash(self.company, self.title, self.location)


def normalize_title(title: str) -> str:
    without_ref = re.sub(r"\s*\(#\d+\)\s*$", "", title.strip())
    return re.sub(r"\s+", " ", without_ref).lower()


def role_key(company: str, title: str) -> tuple[str, str]:
    return normalize_token(company), normalize_title(title)


def compute_hash(company: str, title: str, location: str | None) -> str:
    raw = "|".join(
        [
            normalize_token(company),
            normalize_title(title),
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
    if any(word in text for word in ("remote", "remotely")):
        return "remote"
    if "hybrid" in text:
        return "hybrid"
    if any(word in text for word in ("onsite", "office")):
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

    source_job_id: str | None = None
    raw_source_job_id = raw.get("source_job_id") or raw.get("job_id") or raw.get("id")
    if raw_source_job_id is not None:
        source_job_id = str(raw_source_job_id).strip() or None

    return Vacancy(
        company=company,
        title=title,
        url=url,
        source=str(raw.get("source", "company")),
        location=location,
        remote=str(remote),
        published_at=published_at,
        description=description,
        source_job_id=source_job_id,
    )


def normalize_many(raw_jobs: list[dict[str, Any]]) -> list[Vacancy]:
    vacancies: list[Vacancy] = []
    for raw in raw_jobs:
        vacancy = normalize_raw(raw)
        if vacancy:
            vacancies.append(vacancy)
    return vacancies
