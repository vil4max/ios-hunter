from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

from collector.results import source_failed, source_ok
from collector.types import SourceResult
from integrations.http_client import fetch_json
from parser.normalize import is_ios_job, is_relevant_job_location

_SOURCE_NAME = "Djinni"
_SOURCE_ID = "djinni"
_SOURCE_URL = "https://djinni.co/jobs/?search_type=basic-search&primary_keyword=iOS"
_API_URL = "https://djinni.co/api/jobs/"
_CATEGORIES = ("iOS", "Swift")
_PAGE_SIZE = 50
_MAX_PAGES = 20


def _map_remote(work_format: str | None) -> str:
    text = (work_format or "").lower()
    if "full remote" in text or text.strip() == "remote":
        return "remote"
    if "hybrid" in text:
        return "hybrid"
    if "office" in text or "onsite" in text or "on-site" in text:
        return "onsite"
    if "remote" in text:
        return "remote"
    return "unknown"


def _location_label(item: dict[str, Any]) -> str | None:
    parts: list[str] = []
    location = str(item.get("location") or "").strip()
    if location:
        parts.append(location)
    if item.get("is_ukraine_only"):
        parts.append("Ukraine")
    work_format = str(item.get("work_format") or "").strip()
    if work_format and not location:
        parts.append(work_format)
    return " · ".join(parts) if parts else None


def _job_from_item(item: dict[str, Any]) -> dict[str, Any] | None:
    title = str(item.get("title") or "").strip()
    slug = str(item.get("slug") or "").strip()
    company = str(item.get("company_name") or "").strip() or _SOURCE_NAME
    description = item.get("long_description")
    if description is not None:
        description = str(description).strip() or None
    if not title or not slug:
        return None
    if not is_ios_job(title, description):
        return None

    location = _location_label(item)
    if not is_relevant_job_location(location):
        return None

    return {
        "company": company,
        "title": title,
        "url": f"https://djinni.co/jobs/{slug}/",
        "source": "djinni",
        "source_job_id": str(item.get("id")) if item.get("id") is not None else slug.split("-", 1)[0],
        "description": description,
        "location": location,
        "remote": _map_remote(str(item.get("work_format") or "")),
        "published_at": item.get("published"),
    }


def fetch_category_jobs(category: str) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    offset = 0
    for _ in range(_MAX_PAGES):
        query = urlencode({"category": category, "limit": _PAGE_SIZE, "offset": offset})
        payload = fetch_json(f"{_API_URL}?{query}")
        if not isinstance(payload, dict):
            break
        results = payload.get("results") or []
        if not isinstance(results, list) or not results:
            break
        jobs.extend(item for item in results if isinstance(item, dict))
        total = int(payload.get("count") or 0)
        offset += len(results)
        if offset >= total:
            break
    return jobs


def collect_djinni() -> SourceResult:
    started = time.perf_counter()
    try:
        by_id: dict[str, dict[str, Any]] = {}
        seen: set[str] = set()
        scanned = 0
        for category in _CATEGORIES:
            for item in fetch_category_jobs(category):
                scanned += 1
                job_id = str(item.get("id") or item.get("slug") or "")
                if not job_id or job_id in seen:
                    continue
                seen.add(job_id)
                job = _job_from_item(item)
                if job is not None:
                    by_id[job_id] = job
        jobs = list(by_id.values())
        return source_ok(
            _SOURCE_NAME,
            _SOURCE_URL,
            jobs,
            started,
            scanned=scanned,
            source_id=_SOURCE_ID,
        )
    except Exception as error:  # noqa: BLE001
        return source_failed(_SOURCE_NAME, _SOURCE_URL, error, started, source_id=_SOURCE_ID)
