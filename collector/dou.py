from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests

from parser.normalize import is_ios_job

from collector.results import source_failed, source_ok
from collector.types import SourceResult

IOS_MACOS_FEED_URL = "https://jobs.dou.ua/vacancies/feeds/?category=iOS/macOS"
USER_AGENT = "ios-hunter/2.0 (+https://github.com/)"
RSS_TITLE_PATTERN = re.compile(r"^(?P<title>.+?)\s+в\s+(?P<rest>.+)$")
_REMOTE_UA = re.compile(r"(?i)\b(віддалено|remote)\b")


def _fetch_text(url: str, session: requests.Session) -> str:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def parse_rss_title(raw_title: str) -> tuple[str, str, str | None]:
    match = RSS_TITLE_PATTERN.match(raw_title.strip())
    if not match:
        return raw_title.strip(), "DOU", None
    role = match.group("title").strip()
    parts = [part.strip() for part in match.group("rest").split(",") if part.strip()]
    if not parts:
        return role, "DOU", None
    company = parts[0]
    location = ", ".join(parts[1:]) if len(parts) > 1 else None
    return role, company, location


def _remote_from_location(location: str | None) -> str:
    text = location or ""
    if _REMOTE_UA.search(text):
        return "remote"
    return "unknown"


def parse_dou_category_rss(xml_text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in root.findall("./channel/item"):
        raw_title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not raw_title or not link:
            continue
        title, company, location = parse_rss_title(raw_title)
        if not is_ios_job(title):
            continue
        url = link.split("?", 1)[0]
        if url in seen:
            continue
        seen.add(url)
        vacancy_id_match = re.search(r"/vacancies/(\d+)/", link)
        jobs.append(
            {
                "company": company,
                "title": title,
                "url": url,
                "source": "dou",
                "source_job_id": vacancy_id_match.group(1) if vacancy_id_match else None,
                "location": location,
                "remote": _remote_from_location(location),
            }
        )
    return jobs


def collect_dou_ios_rss() -> SourceResult:
    started = time.perf_counter()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    try:
        xml_text = _fetch_text(IOS_MACOS_FEED_URL, session)
        root = ET.fromstring(xml_text)
        scanned = len(root.findall("./channel/item"))
        jobs = parse_dou_category_rss(xml_text)
        return source_ok(
            "DOU iOS/macOS",
            IOS_MACOS_FEED_URL,
            jobs,
            started,
            scanned=scanned,
            source_id="dou-ios-rss",
        )
    except Exception as error:  # noqa: BLE001
        return source_failed(
            "DOU iOS/macOS",
            IOS_MACOS_FEED_URL,
            error,
            started,
            source_id="dou-ios-rss",
        )


def collect_dou_company_feed(company: str, slug: str) -> SourceResult:
    started = time.perf_counter()
    feed_url = f"https://jobs.dou.ua/vacancies/{slug}/feeds/"
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    try:
        xml_text = _fetch_text(feed_url, session)
        root = ET.fromstring(xml_text)
        scanned = len(root.findall("./channel/item"))
        jobs = parse_dou_category_rss(xml_text)
        for job in jobs:
            job["company"] = company
        return source_ok(company, feed_url, jobs, started, scanned=scanned)
    except Exception as error:  # noqa: BLE001
        return source_failed(company, feed_url, error, started)
