from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from collector.types import SourceResult
from integrations.http_client import fetch_json


def load_swift_export(path: str | Path) -> list[dict[str, Any]]:
    export_path = Path(path)
    if not export_path.exists():
        return []
    data = json.loads(export_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("jobs", [])


def _is_ios_title(title: str) -> bool:
    lowered = title.lower()
    return "ios" in lowered or "swift" in lowered


def collect_teamtailor(company: str, feed_url: str) -> SourceResult:
    started = time.perf_counter()
    try:
        payload = fetch_json(feed_url)
        jobs = []
        for item in payload.get("jobs", payload if isinstance(payload, list) else []):
            title = str(item.get("title", ""))
            if not _is_ios_title(title):
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": item.get("url") or item.get("links", {}).get("careersite-job-url", ""),
                    "source": "company",
                    "description": item.get("body") or item.get("description"),
                    "location": (item.get("location") or {}).get("city")
                    if isinstance(item.get("location"), dict)
                    else item.get("location"),
                }
            )
        elapsed = int((time.perf_counter() - started) * 1000)
        return SourceResult(
            source_id=f"company:{company.lower()}",
            source_name=company,
            source_url=feed_url,
            jobs=jobs,
            status="healthy",
            error=None,
            response_ms=elapsed,
        )
    except Exception as error:  # noqa: BLE001
        elapsed = int((time.perf_counter() - started) * 1000)
        return SourceResult(
            source_id=f"company:{company.lower()}",
            source_name=company,
            source_url=feed_url,
            jobs=[],
            status="failed",
            error=str(error),
            response_ms=elapsed,
        )


def collect_greenhouse(company: str, board_slug: str) -> SourceResult:
    """
    Greenhouse public boards API.
    Endpoint: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
    """
    started = time.perf_counter()
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs?content=true"
    try:
        payload = fetch_json(url)
        jobs: list[dict[str, Any]] = []
        for item in payload.get("jobs", []):
            title = str(item.get("title", ""))
            if not _is_ios_title(title):
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": item.get("absolute_url") or item.get("url") or "",
                    "source": "company",
                    "description": item.get("content"),
                    "location": (item.get("location") or {}).get("name")
                    if isinstance(item.get("location"), dict)
                    else item.get("location"),
                    "updated_at": item.get("updated_at"),
                }
            )
        elapsed = int((time.perf_counter() - started) * 1000)
        return SourceResult(
            source_id=f"company:{company.lower()}",
            source_name=company,
            source_url=url,
            jobs=jobs,
            status="healthy",
            error=None,
            response_ms=elapsed,
        )
    except Exception as error:  # noqa: BLE001
        elapsed = int((time.perf_counter() - started) * 1000)
        return SourceResult(
            source_id=f"company:{company.lower()}",
            source_name=company,
            source_url=url,
            jobs=[],
            status="failed",
            error=str(error),
            response_ms=elapsed,
        )


def collect_ashby(company: str, board_slug: str) -> SourceResult:
    """
    Ashby public posting API.
    Endpoint: https://api.ashbyhq.com/posting-api/job-board/{slug}
    """
    started = time.perf_counter()
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board_slug}"
    try:
        payload = fetch_json(url)
        jobs: list[dict[str, Any]] = []
        for item in payload.get("jobs", []):
            title = str(item.get("title", ""))
            if not _is_ios_title(title):
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": item.get("jobUrl") or item.get("applyUrl") or "",
                    "source": "company",
                    "description": item.get("descriptionPlain") or item.get("descriptionHtml"),
                    "location": item.get("location"),
                }
            )
        elapsed = int((time.perf_counter() - started) * 1000)
        return SourceResult(
            source_id=f"company:{company.lower()}",
            source_name=company,
            source_url=url,
            jobs=jobs,
            status="healthy",
            error=None,
            response_ms=elapsed,
        )
    except Exception as error:  # noqa: BLE001
        elapsed = int((time.perf_counter() - started) * 1000)
        return SourceResult(
            source_id=f"company:{company.lower()}",
            source_name=company,
            source_url=url,
            jobs=[],
            status="failed",
            error=str(error),
            response_ms=elapsed,
        )


def collect_lever(company: str, board_slug: str) -> SourceResult:
    """
    Lever public postings API.
    Endpoint: https://api.lever.co/v0/postings/{slug}?mode=json
    """
    started = time.perf_counter()
    url = f"https://api.lever.co/v0/postings/{board_slug}?mode=json"
    try:
        payload = fetch_json(url)
        items = payload if isinstance(payload, list) else []
        jobs: list[dict[str, Any]] = []
        for item in items:
            title = str(item.get("text", ""))
            if not _is_ios_title(title):
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": item.get("hostedUrl") or item.get("applyUrl") or "",
                    "source": "company",
                    "description": item.get("descriptionPlain") or item.get("description"),
                    "location": item.get("categories", {}).get("location"),
                    "updated_at": item.get("createdAt"),
                }
            )
        elapsed = int((time.perf_counter() - started) * 1000)
        return SourceResult(
            source_id=f"company:{company.lower()}",
            source_name=company,
            source_url=url,
            jobs=jobs,
            status="healthy",
            error=None,
            response_ms=elapsed,
        )
    except Exception as error:  # noqa: BLE001
        elapsed = int((time.perf_counter() - started) * 1000)
        return SourceResult(
            source_id=f"company:{company.lower()}",
            source_name=company,
            source_url=url,
            jobs=[],
            status="failed",
            error=str(error),
            response_ms=elapsed,
        )


def collect_all(swift_export_path: str | Path = "database/swift_export.json") -> list[SourceResult]:
    results: list[SourceResult] = []

    swift_jobs = load_swift_export(swift_export_path)
    if swift_jobs:
        results.append(
            SourceResult(
                source_id="swift-export",
                source_name="Swift Collector",
                source_url=None,
                jobs=swift_jobs,
                status="healthy",
                error=None,
                response_ms=0,
            )
        )

    results.append(collect_teamtailor("Levi9", "https://jobs.ua.levi9.com/jobs.json"))
    results.append(collect_teamtailor("Avenga", "https://career.avenga.com/jobs.json"))
    results.append(collect_greenhouse("Readdle", "readdle70"))
    results.append(collect_ashby("Preply", "preply"))
    results.append(collect_greenhouse("N-iX", "nix"))
    results.append(collect_lever("ELEKS", "eleks"))
    return results
