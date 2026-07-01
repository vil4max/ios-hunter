from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Any

from collector.types import SourceResult


def load_swift_export(path: str | Path) -> list[dict[str, Any]]:
    export_path = Path(path)
    if not export_path.exists():
        return []
    data = json.loads(export_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("jobs", [])


def fetch_json(url: str, timeout: int = 30) -> Any:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ios-hunter/2.0 (+https://github.com/)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def collect_teamtailor(company: str, feed_url: str) -> SourceResult:
    started = time.perf_counter()
    try:
        payload = fetch_json(feed_url)
        jobs = []
        for item in payload.get("jobs", payload if isinstance(payload, list) else []):
            title = str(item.get("title", ""))
            if "ios" not in title.lower() and "swift" not in title.lower():
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
    return results
