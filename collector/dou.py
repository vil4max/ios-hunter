from __future__ import annotations

import logging
from typing import Any

import requests
from bs4 import BeautifulSoup

from collector.types import SourceResult

logger = logging.getLogger(__name__)


def collect_dou() -> SourceResult:
    url = "https://jobs.dou.ua/vacancies/?category=Swift"
    return _collect_html("dou", "DOU", url, source="dou")


def collect_djinni() -> SourceResult:
    url = "https://djinni.co/jobs/?primary_keyword=ios"
    return _collect_html("djinni", "Djinni", url, source="djinni")


def collect_linkedin() -> SourceResult:
    logger.warning("LinkedIn collector is a stub — not implemented")
    return SourceResult(
        source_id="linkedin",
        source_name="LinkedIn",
        source_url=None,
        jobs=[],
        status="healthy",
        error="stub",
        response_ms=0,
    )


def _collect_html(source_id: str, name: str, url: str, source: str) -> SourceResult:
    import time

    started = time.perf_counter()
    try:
        response = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "ios-hunter/2.0"},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        jobs: list[dict[str, Any]] = []

        if source_id == "dou":
            for link in soup.select("a.vt"):
                title = link.get_text(strip=True)
                if "ios" not in title.lower() and "swift" not in title.lower():
                    continue
                href = link.get("href", "")
                job_url = href if href.startswith("http") else f"https://jobs.dou.ua{href}"
                company_node = link.find_parent().select_one("a.company") if link.find_parent() else None
                company = company_node.get_text(strip=True) if company_node else "Unknown"
                jobs.append({"company": company, "title": title, "url": job_url, "source": source})
        else:
            for item in soup.select("li.list-jobs__item"):
                link = item.select_one("a.job-list-item__link")
                if not link:
                    continue
                title = link.get_text(strip=True)
                if "ios" not in title.lower() and "swift" not in title.lower():
                    continue
                href = link.get("href", "")
                job_url = href if href.startswith("http") else f"https://djinni.co{href}"
                company_node = item.select_one("a")
                company = company_node.get_text(strip=True) if company_node else "Unknown"
                jobs.append({"company": company, "title": title, "url": job_url, "source": source})

        elapsed = int((time.perf_counter() - started) * 1000)
        return SourceResult(
            source_id=source_id,
            source_name=name,
            source_url=url,
            jobs=jobs,
            status="healthy",
            error=None,
            response_ms=elapsed,
        )
    except Exception as error:  # noqa: BLE001
        elapsed = int((time.perf_counter() - started) * 1000)
        return SourceResult(
            source_id=source_id,
            source_name=name,
            source_url=url,
            jobs=[],
            status="failed",
            error=str(error),
            response_ms=elapsed,
        )
