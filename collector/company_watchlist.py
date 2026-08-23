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
from integrations.http_client import fetch_impersonated, fetch_json, fetch_text, post_json
from parser.normalize import is_ios_job

_JOB_URL_TOKENS = ("career", "job", "jobs", "vacanc", "position", "opening")
_ALLOWED_LOCATIONS_BY_COMPANY: dict[str, frozenset[str]] = {
    "zoolatech": frozenset(
        {
            "central europe",
            "eastern europe",
            "europe",
            "remote",
            "ukraine",
        }
    ),
}
_CONSCENSIA_API_URL = "https://careers.conscensia.com/wp-json/wp/v2/job?per_page=100"
_SVITLA_API_URL = "https://svitla.com/career/api/v1/jobs/public?page={page}"
_WORKABLE_WIDGET_URL = "https://apply.workable.com/api/v1/widget/accounts/labelyourdata"
_PLAYRIX_API_URL = "https://playrix.com/api/v1/index.php"


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
    candidates: dict[str, tuple[str, str | None, str | None]],
    *,
    title: str,
    url: str,
    base_url: str,
    description: str | None = None,
    location: str | None = None,
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
    candidates.setdefault(absolute_url, (normalized_title, description, location))


def _local_description(anchor) -> str | None:
    parent = anchor.parent
    if parent is None:
        return None
    job_links = [
        link
        for link in parent.select("a[href]")
        if _is_job_url(urljoin("https://example.invalid", str(link.get("href") or "")))
    ]
    if len(job_links) > 1:
        return None
    return parent.get_text(" ", strip=True) or None


def _local_location(company: str, anchor) -> str | None:
    country = anchor.select_one(".country")
    if country is not None:
        return country.get_text(" ", strip=True) or None
    if company.strip().lower() == "avenga":
        metadata = anchor.find_next_sibling("div", class_=lambda value: value and "mt-1" in value)
        if metadata is not None:
            return metadata.get_text(" ", strip=True) or None
    return None


def _location_is_allowed(company: str, location: str | None) -> bool:
    allowed = _ALLOWED_LOCATIONS_BY_COMPANY.get(company.strip().lower())
    if not allowed or not location:
        return True
    return location.strip().lower() in allowed


def extract_ios_jobs(company: str, page_url: str, html: str) -> tuple[list[dict[str, Any]], int]:
    document = BeautifulSoup(html, "lxml")
    candidates: dict[str, tuple[str, str | None, str | None]] = {}
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
            description=_local_description(anchor),
            location=_local_location(company, anchor),
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
    for url, (title, description, location) in candidates.items():
        if not _location_is_allowed(company, location):
            continue
        job = {"company": company, "title": title, "url": url, "source": "company"}
        if description:
            job["description"] = description
        if location:
            job["location"] = location
        jobs.append(job)
    return jobs, len(job_like_links)


def _collect_conscensia(company: str) -> tuple[list[dict[str, Any]], int]:
    try:
        payload = fetch_json(_CONSCENSIA_API_URL)
    except requests.HTTPError as error:
        status = error.response.status_code if error.response is not None else 0
        if status not in {403, 429, 454}:
            raise
        payload = json.loads(fetch_impersonated(_CONSCENSIA_API_URL))
    if not isinstance(payload, list):
        raise RuntimeError("Conscensia API returned an unexpected payload")
    items = payload
    jobs: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title_node = item.get("title")
        title = str(title_node.get("rendered") or "") if isinstance(title_node, dict) else ""
        description = str(item.get("content") or "")
        if not is_ios_job(title, description):
            continue
        jobs.append(
            {
                "company": company,
                "title": title,
                "url": str(item.get("link") or ""),
                "source": "company",
                "source_job_id": str(item.get("id") or ""),
            }
        )
    return jobs, len(items)


def _collect_svitla(company: str) -> tuple[list[dict[str, Any]], int]:
    jobs: list[dict[str, Any]] = []
    scanned = 0
    page = 1
    while True:
        payload = fetch_json(_SVITLA_API_URL.format(page=page))
        if not isinstance(payload, dict):
            raise RuntimeError("Svitla API returned an unexpected payload")
        items = payload.get("items")
        if not isinstance(items, list):
            raise RuntimeError("Svitla API payload is missing items")
        scanned += len(items)
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("position") or "").strip()
            description = str(item.get("fullDescription") or "")
            if not is_ios_job(title, description):
                continue
            cities = item.get("jobCities") if isinstance(item.get("jobCities"), list) else []
            locations = []
            for entry in cities:
                city = entry.get("city") if isinstance(entry, dict) else None
                if not isinstance(city, dict):
                    continue
                label = ", ".join(
                    part
                    for part in (str(city.get("name") or "").strip(), str(city.get("country") or "").strip())
                    if part and part.lower() != "any city"
                )
                if label:
                    locations.append(label)
            slug = str(item.get("slug") or "").strip()
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": urljoin("https://svitla.com/career/job/", slug),
                    "source": "company",
                    "source_job_id": str(item.get("id") or ""),
                    "location": " / ".join(dict.fromkeys(locations)) or None,
                    "description": description or None,
                }
            )
        total_pages = int(payload.get("pages") or 1)
        if page >= total_pages:
            break
        page += 1
    return jobs, scanned


def _collect_label_your_data(company: str) -> tuple[list[dict[str, Any]], int]:
    payload = fetch_json(_WORKABLE_WIDGET_URL)
    if not isinstance(payload, dict):
        raise RuntimeError("Workable API returned an unexpected payload")
    items = payload.get("jobs")
    if not isinstance(items, list):
        raise RuntimeError("Workable API payload is missing jobs")
    jobs: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not is_ios_job(title):
            continue
        locations = item.get("locations") if isinstance(item.get("locations"), list) else []
        location_labels = []
        for location in locations:
            if not isinstance(location, dict):
                continue
            label = ", ".join(
                part
                for part in (str(location.get("city") or "").strip(), str(location.get("country") or "").strip())
                if part
            )
            if label:
                location_labels.append(label)
        jobs.append(
            {
                "company": company,
                "title": title,
                "url": str(item.get("url") or item.get("shortlink") or ""),
                "source": "company",
                "source_job_id": str(item.get("shortcode") or ""),
                "location": " / ".join(dict.fromkeys(location_labels)) or None,
                "remote": "remote" if item.get("telecommuting") else "unknown",
            }
        )
    return jobs, len(items)


def _playrix_payload(action: str) -> dict[str, Any]:
    payload = post_json(
        _PLAYRIX_API_URL,
        {"action": action, "options": {"lang": "en"}},
        params={"action": action},
    )
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise RuntimeError(f"Playrix API failed for {action}")
    return payload


def _collect_playrix(company: str) -> tuple[list[dict[str, Any]], int]:
    jobs_payload = _playrix_payload("job/getList")
    sections_payload = _playrix_payload("job/getSectionList")
    items = jobs_payload.get("items")
    sections = sections_payload.get("items")
    if not isinstance(items, list) or not isinstance(sections, list):
        raise RuntimeError("Playrix API payload is missing items")
    section_codes = {
        item.get("id"): str(item.get("code") or "")
        for item in sections
        if isinstance(item, dict)
    }
    visible_items = [
        item for item in items if isinstance(item, dict) and item.get("isHidden") is not True
    ]
    jobs: list[dict[str, Any]] = []
    for item in visible_items:
        title = str(item.get("name") or "").strip()
        description = " ".join(
            str(item.get(field) or "")
            for field in (
                "previewText",
                "detailText",
                "responsibilities",
                "requirements",
                "ourStack",
            )
        )
        if not is_ios_job(title, description):
            continue
        section = section_codes.get(item.get("parentId"), "")
        slug = str(item.get("code") or "").strip()
        if not section or not slug:
            raise RuntimeError("Playrix job is missing its URL components")
        jobs.append(
            {
                "company": company,
                "title": title,
                "url": f"https://playrix.com/job/open/{section}/{slug}",
                "source": "company",
                "source_job_id": str(item.get("id") or ""),
                "description": description or None,
                "remote": str(item.get("workFormat") or "unknown"),
            }
        )
    return jobs, len(visible_items)


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
        if slug == "conscensia":
            jobs, scanned = _collect_conscensia(name)
            return source_ok(name, career_url, jobs, started, scanned=scanned, source_id=source_id)
        if slug == "svitla-systems-inc":
            jobs, scanned = _collect_svitla(name)
            return source_ok(name, career_url, jobs, started, scanned=scanned, source_id=source_id)
        if slug == "label-your-data":
            jobs, scanned = _collect_label_your_data(name)
            return source_ok(name, career_url, jobs, started, scanned=scanned, source_id=source_id)
        if slug == "playrix":
            jobs, scanned = _collect_playrix(name)
            return source_ok(name, career_url, jobs, started, scanned=scanned, source_id=source_id)
        fetch_url = career_url
        try:
            html = fetch_text(fetch_url)
        except requests.HTTPError as error:
            status = error.response.status_code if error.response is not None else 0
            if status not in {403, 429}:
                raise
            html = fetch_impersonated(fetch_url)
        jobs, scanned = extract_ios_jobs(name, fetch_url, html)
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
