from __future__ import annotations

import json
import re
import time
from typing import Any

from collector.results import source_failed, source_ok
from collector.types import SourceResult
from integrations.http_client import fetch_impersonated
from parser.normalize import is_ios_job, is_relevant_job_location

_SOURCE_NAME = "Indeed UA"
_SOURCE_ID = "indeed"
_SOURCE_URL = "https://ua.indeed.com/jobs?q=iOS"
_WARM_URL = "https://ua.indeed.com/"
_JOBCARDS_MARKER = 'window.mosaic.providerData["mosaic-provider-jobcards"]='
_HTML_TAG = re.compile(r"<[^>]+>")


def _fetch_search_html(url: str = _SOURCE_URL) -> str:
    return fetch_impersonated(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
        },
        warm_urls=(_WARM_URL,),
        accept=lambda text: _JOBCARDS_MARKER in text,
    )

def _extract_json_object(text: str, start: int) -> dict[str, Any]:
    if start < 0 or start >= len(text) or text[start] != "{":
        raise ValueError("expected JSON object start")
    depth = 0
    in_str = False
    esc = False
    for index in range(start, len(text)):
        char = text[index]
        if in_str:
            if esc:
                esc = False
            elif char == "\\":
                esc = True
            elif char == '"':
                in_str = False
            continue
        if char == '"':
            in_str = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                payload = json.loads(text[start : index + 1])
                if not isinstance(payload, dict):
                    raise ValueError("jobcards payload is not an object")
                return payload
    raise ValueError("unclosed JSON object in Indeed HTML")


def parse_jobcards_html(html: str) -> list[dict[str, Any]]:
    marker_at = html.find(_JOBCARDS_MARKER)
    if marker_at < 0:
        raise ValueError("mosaic-provider-jobcards not found")
    payload = _extract_json_object(html, marker_at + len(_JOBCARDS_MARKER))
    model = ((payload.get("metaData") or {}).get("mosaicProviderJobCardsModel") or {})
    results = model.get("results") or []
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, dict)]


def _snippet_text(item: dict[str, Any]) -> str | None:
    raw = item.get("snippet") or item.get("jobSnippet") or ""
    text = _HTML_TAG.sub(" ", str(raw))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _map_remote(item: dict[str, Any], location: str | None) -> str:
    if item.get("remoteLocation") or item.get("isJobRemote"):
        return "remote"
    text = f"{location or ''} {item.get('title') or ''}".lower()
    if "дистанц" in text or "remote" in text:
        return "remote"
    if "hybrid" in text:
        return "hybrid"
    return "unknown"


def _job_from_item(item: dict[str, Any]) -> dict[str, Any] | None:
    title = str(item.get("title") or item.get("displayTitle") or "").strip()
    jobkey = str(item.get("jobkey") or item.get("jobKey") or "").strip()
    company = str(item.get("company") or item.get("companyName") or "").strip() or _SOURCE_NAME
    if not title or not jobkey:
        return None

    description = _snippet_text(item)
    if not is_ios_job(title, description):
        return None

    location = str(item.get("formattedLocation") or item.get("jobLocationCity") or "").strip() or None
    if not is_relevant_job_location(location):
        return None

    return {
        "company": company,
        "title": title,
        "url": f"https://ua.indeed.com/viewjob?jk={jobkey}",
        "source": "indeed",
        "source_job_id": jobkey,
        "description": description,
        "location": location,
        "remote": _map_remote(item, location),
    }


def collect_indeed() -> SourceResult:
    started = time.perf_counter()
    try:
        html = _fetch_search_html()
        scanned = 0
        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in parse_jobcards_html(html):
            scanned += 1
            job = _job_from_item(item)
            if job is None:
                continue
            job_id = str(job["source_job_id"])
            if job_id in seen:
                continue
            seen.add(job_id)
            jobs.append(job)
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
