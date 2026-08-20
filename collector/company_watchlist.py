from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from collector.results import source_failed, source_ok
from collector.types import SourceResult
from integrations.http_client import fetch_impersonated, fetch_text
from parser.normalize import is_ios_job

_JOB_URL_TOKENS = ("career", "job", "jobs", "vacanc", "position", "opening")


def default_watchlist_path(root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parents[1]
    return base / "database" / "dou_service_companies.json"


def load_company_watchlist(path: Path | None = None) -> list[dict[str, Any]]:
    payload = json.loads((path or default_watchlist_path()).read_text(encoding="utf-8"))
    companies = payload.get("companies") if isinstance(payload, dict) else None
    if not isinstance(companies, list):
        raise ValueError("company watchlist must contain a companies list")
    return [company for company in companies if isinstance(company, dict)]


def _is_job_url(url: str) -> bool:
    value = url.lower()
    return any(token in value for token in _JOB_URL_TOKENS)


def _add_candidate(
    candidates: dict[str, tuple[str, str | None]],
    *,
    title: str,
    url: str,
    base_url: str,
    description: str | None = None,
    is_job_posting: bool = False,
) -> None:
    normalized_title = " ".join(title.split())
    absolute_url = urljoin(base_url, url.strip())
    if not normalized_title or not absolute_url.startswith(("http://", "https://")):
        return
    if not is_job_posting and not _is_job_url(absolute_url):
        return
    if not (is_ios_job(normalized_title, description) or is_ios_job(absolute_url)):
        return
    candidates.setdefault(absolute_url, (normalized_title, description))


def extract_ios_jobs(company: str, page_url: str, html: str) -> tuple[list[dict[str, Any]], int]:
    document = BeautifulSoup(html, "lxml")
    candidates: dict[str, tuple[str, str | None]] = {}
    job_like_links: set[str] = set()

    for anchor in document.select("a[href]"):
        href = str(anchor.get("href") or "").strip()
        if not href:
            continue
        absolute_url = urljoin(page_url, href)
        if _is_job_url(absolute_url):
            job_like_links.add(absolute_url)
        _add_candidate(
            candidates,
            title=anchor.get_text(" ", strip=True),
            url=href,
            base_url=page_url,
            description=anchor.parent.get_text(" ", strip=True) if anchor.parent else None,
        )

    for script in document.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.string or "")
        except (TypeError, ValueError):
            continue
        entries = payload if isinstance(payload, list) else [payload]
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("@type") != "JobPosting":
                continue
            title = str(entry.get("title") or "")
            url = str(entry.get("url") or page_url)
            description = str(entry.get("description") or "") or None
            job_like_links.add(urljoin(page_url, url))
            _add_candidate(
                candidates,
                title=title,
                url=url,
                base_url=page_url,
                description=description,
                is_job_posting=True,
            )

    jobs = []
    for url, (title, description) in candidates.items():
        job = {"company": company, "title": title, "url": url, "source": "company"}
        if description:
            job["description"] = description
        jobs.append(job)
    return jobs, len(job_like_links)


def collect_watchlist_company(company: dict[str, Any]) -> SourceResult:
    name = str(company.get("name") or "Unknown company").strip()
    slug = str(company.get("slug") or name.lower()).strip()
    career_url = str(company.get("career_url") or "").strip()
    source_id = f"company-watchlist:{slug}"
    started = time.perf_counter()
    if not career_url:
        fallback_url = str(company.get("company_site_url") or company.get("dou_company_url") or "")
        return source_failed(
            name,
            fallback_url,
            "official career URL unresolved",
            started,
            source_id=source_id,
        )
    try:
        try:
            html = fetch_text(career_url)
        except requests.HTTPError as error:
            status = error.response.status_code if error.response is not None else 0
            if status not in {403, 429}:
                raise
            html = fetch_impersonated(career_url)
        jobs, scanned = extract_ios_jobs(name, career_url, html)
        return source_ok(
            name,
            career_url,
            jobs,
            started,
            scanned=scanned,
            source_id=source_id,
        )
    except Exception as error:  # noqa: BLE001
        return source_failed(name, career_url, error, started, source_id=source_id)
