from __future__ import annotations

import html
import json
import re
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from parser.normalize import is_ios_job

COMPANY_SITE_PATTERN = re.compile(
    r'<div class="site">\s*<a href="([^"]+)" target="_blank" rel="nofollow">',
    re.IGNORECASE | re.DOTALL,
)
GENERIC_VACANCY_PATTERN = re.compile(
    r'<a[^>]+href="([^"]+)"[^>]*>\s*([^<]+)\s*</a>',
    re.IGNORECASE | re.DOTALL,
)
GREENHOUSE_BOARD_PATTERN = re.compile(
    r"boards-api\.greenhouse\.io/v1/boards/([^/\"']+)/jobs",
    re.IGNORECASE,
)


def extract_company_site_url(profile_html: str) -> str | None:
    match = COMPANY_SITE_PATTERN.search(profile_html)
    if not match:
        return None
    return html.unescape(match.group(1).strip())


def _normalize_fetch_url(url: str) -> str:
    cleaned = html.unescape(url.strip())
    return cleaned.replace("&amp;", "&")


def _job_dict(company: str, title: str, url: str, source_job_id: str | None = None) -> dict[str, Any]:
    return {
        "company": company,
        "title": title.strip(),
        "url": url,
        "source": "company",
        "source_job_id": source_job_id,
    }


def _try_teamtailor_jobs(company: str, site_url: str, session: requests.Session) -> list[dict[str, Any]]:
    parsed = urlparse(_normalize_fetch_url(site_url))
    origin = f"{parsed.scheme}://{parsed.netloc}"
    feed_url = urljoin(origin + "/", "jobs.json")
    try:
        response = session.get(feed_url, timeout=30)
        if response.status_code != 200:
            return []
        payload = response.json()
    except (requests.RequestException, json.JSONDecodeError, ValueError):
        return []

    jobs: list[dict[str, Any]] = []
    items = payload.get("jobs", payload if isinstance(payload, list) else [])
    if not isinstance(items, list):
        return []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not is_ios_job(title):
            continue
        job_url = item.get("url") or (item.get("links") or {}).get("careersite-job-url") or ""
        if not job_url:
            continue
        jobs.append(
            _job_dict(
                company,
                title,
                str(job_url),
                str(item.get("id") or item.get("job_id") or "") or None,
            )
        )
    return jobs


def _try_greenhouse_jobs(company: str, page_html: str, session: requests.Session) -> list[dict[str, Any]]:
    match = GREENHOUSE_BOARD_PATTERN.search(page_html)
    if not match:
        return []
    board_slug = match.group(1)
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs?content=true"
    try:
        response = session.get(api_url, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, json.JSONDecodeError, ValueError):
        return []

    jobs: list[dict[str, Any]] = []
    for item in payload.get("jobs", []):
        title = str(item.get("title", "")).strip()
        if not is_ios_job(title):
            continue
        job_url = item.get("absolute_url") or item.get("url") or ""
        if not job_url:
            continue
        jobs.append(_job_dict(company, title, str(job_url), str(item.get("id") or "") or None))
    return jobs


def _scrape_generic_careers(company: str, site_url: str, page_html: str) -> list[dict[str, Any]]:
    base_url = _normalize_fetch_url(site_url)
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()

    for match in GENERIC_VACANCY_PATTERN.finditer(page_html):
        href = unescape(match.group(1).strip())
        title = unescape(match.group(2).strip())
        if not title:
            continue
        if not is_ios_job(title) and not is_ios_job(href):
            continue

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if not parsed.scheme.startswith("http"):
            continue
        lowered = absolute.lower()
        if not any(token in lowered for token in ("vacanc", "job", "career", "position", "opening")):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        jobs.append(_job_dict(company, title, absolute))

    return jobs


def collect_jobs_from_career_site(
    company: str,
    site_url: str,
    session: requests.Session,
) -> list[dict[str, Any]]:
    normalized_url = _normalize_fetch_url(site_url)
    jobs_by_url: dict[str, dict[str, Any]] = {}

    for job in _try_teamtailor_jobs(company, normalized_url, session):
        jobs_by_url[job["url"]] = job

    try:
        response = session.get(normalized_url, timeout=30)
        if response.status_code != 200:
            return list(jobs_by_url.values())
        page_html = response.text
    except requests.RequestException:
        return list(jobs_by_url.values())

    for job in _try_greenhouse_jobs(company, page_html, session):
        jobs_by_url[job["url"]] = job
    for job in _scrape_generic_careers(company, normalized_url, page_html):
        jobs_by_url[job["url"]] = job

    return list(jobs_by_url.values())

