from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import requests

from parser.normalize import is_ios_job

from collector.dou import collect_dou_top50
from collector.types import CollectResult, SourceResult, SwiftCollectorMeta
from integrations.http_client import fetch_json


def load_swift_export(path: str | Path) -> list[dict[str, Any]]:
    export_path = Path(path)
    if not export_path.exists():
        return []
    data = json.loads(export_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("jobs", [])


def load_swift_collector_meta(path: str | Path) -> SwiftCollectorMeta | None:
    export_path = Path(path)
    if not export_path.exists():
        return None
    data = json.loads(export_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    meta = data.get("meta")
    if not isinstance(meta, dict):
        return None
    failed_companies = meta.get("failed_companies", [])
    if not isinstance(failed_companies, list):
        failed_companies = []
    return SwiftCollectorMeta(
        sources_total=int(meta.get("sources_total", 0)),
        sources_failed=int(meta.get("sources_failed", 0)),
        failed_companies=[str(name) for name in failed_companies],
    )


def _source_ok(company: str, source_url: str, jobs: list[dict[str, Any]], started: float) -> SourceResult:
    elapsed = int((time.perf_counter() - started) * 1000)
    return SourceResult(
        source_id=f"company:{company.lower()}",
        source_name=company,
        source_url=source_url,
        jobs=jobs,
        status="healthy",
        error=None,
        response_ms=elapsed,
    )


def _source_failed(company: str, source_url: str, error: Exception, started: float) -> SourceResult:
    elapsed = int((time.perf_counter() - started) * 1000)
    return SourceResult(
        source_id=f"company:{company.lower()}",
        source_name=company,
        source_url=source_url,
        jobs=[],
        status="failed",
        error=str(error),
        response_ms=elapsed,
    )


def collect_teamtailor(company: str, feed_url: str) -> SourceResult:
    started = time.perf_counter()
    try:
        payload = fetch_json(feed_url)
        jobs = []
        for item in payload.get("jobs", payload if isinstance(payload, list) else []):
            title = str(item.get("title", ""))
            if not is_ios_job(title):
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": item.get("url") or item.get("links", {}).get("careersite-job-url", ""),
                    "source": "company",
                    "source_job_id": item.get("id") or item.get("job_id"),
                    "description": item.get("body") or item.get("description"),
                    "location": (item.get("location") or {}).get("city")
                    if isinstance(item.get("location"), dict)
                    else item.get("location"),
                }
            )
        return _source_ok(company, feed_url, jobs, started)
    except Exception as error:  # noqa: BLE001
        return _source_failed(company, feed_url, error, started)


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
            if not is_ios_job(title):
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": item.get("absolute_url") or item.get("url") or "",
                    "source": "company",
                    "source_job_id": item.get("id"),
                    "description": item.get("content"),
                    "location": (item.get("location") or {}).get("name")
                    if isinstance(item.get("location"), dict)
                    else item.get("location"),
                    "updated_at": item.get("updated_at"),
                }
            )
        return _source_ok(company, url, jobs, started)
    except Exception as error:  # noqa: BLE001
        return _source_failed(company, url, error, started)


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
            if not is_ios_job(title):
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": item.get("jobUrl") or item.get("applyUrl") or "",
                    "source": "company",
                    "source_job_id": item.get("id") or item.get("jobId"),
                    "description": item.get("descriptionPlain") or item.get("descriptionHtml"),
                    "location": item.get("location"),
                }
            )
        return _source_ok(company, url, jobs, started)
    except Exception as error:  # noqa: BLE001
        return _source_failed(company, url, error, started)


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
            if not is_ios_job(title):
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": item.get("hostedUrl") or item.get("applyUrl") or "",
                    "source": "company",
                    "source_job_id": item.get("id"),
                    "description": item.get("descriptionPlain") or item.get("description"),
                    "location": item.get("categories", {}).get("location"),
                    "updated_at": item.get("createdAt"),
                }
            )
        return _source_ok(company, url, jobs, started)
    except Exception as error:  # noqa: BLE001
        return _source_failed(company, url, error, started)


def collect_workable_jobs_md(company: str, account_slug: str) -> SourceResult:
    """
    Workable public markdown export.
    Endpoint: https://apply.workable.com/{slug}/jobs.md
    """
    started = time.perf_counter()
    url = f"https://apply.workable.com/{account_slug}/jobs.md"
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "ios-hunter/2.0 (+https://github.com/)"},
            timeout=30,
        )
        response.raise_for_status()
        text = response.text

        jobs: list[dict[str, Any]] = []
        for line in text.splitlines():
            if not line.startswith("| "):
                continue
            if " Title " in line or line.startswith("|-------"):
                continue

            # | Title | Department | Location | Type | Salary | Posted | Details |
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            if len(parts) < 7:
                continue

            title = parts[0]
            if not is_ios_job(title):
                continue

            location = parts[2]
            details = parts[6]
            match = re.search(r"\((https?://[^)]+)\)", details)
            job_url = match.group(1) if match else ""

            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": job_url,
                    "source": "company",
                    "location": location,
                }
            )

        return _source_ok(company, url, jobs, started)
    except Exception as error:  # noqa: BLE001
        return _source_failed(company, url, error, started)


def collect_all(swift_export_path: str | Path = "database/swift_export.json") -> CollectResult:
    results: list[SourceResult] = []
    swift_meta = load_swift_collector_meta(swift_export_path)

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
    results.append(collect_workable_jobs_md("Globaldev Group", "globaldevgroup"))
    results.append(collect_workable_jobs_md("Intetics", "intetics-2"))
    results.append(collect_workable_jobs_md("Intersog", "intersog-na"))
    results.append(collect_workable_jobs_md("Romexsoft", "romexsoft"))
    results.append(collect_workable_jobs_md("SupportYourApp", "supportyourapp"))
    results.append(collect_dou_top50())
    return CollectResult(source_results=results, swift_meta=swift_meta)
