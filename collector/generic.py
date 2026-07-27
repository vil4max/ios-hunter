from __future__ import annotations

import html as html_lib
import re
import time
from typing import Any, Callable
from urllib.parse import urljoin

from collector.results import source_failed, source_ok
from collector.types import SourceResult
from integrations.http_client import fetch_json, fetch_text, fetch_text_allowing_bot_wall
from parser.normalize import is_ios_job


def collect_workable_widget(company: str, account_slug: str) -> SourceResult:
    started = time.perf_counter()
    url = f"https://apply.workable.com/api/v1/widget/accounts/{account_slug}"
    try:
        payload = fetch_json(url)
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in items:
            title = str(item.get("title", ""))
            job_url = str(item.get("url") or "")
            if not job_url or job_url in seen:
                continue
            seen.add(job_url)
            if not is_ios_job(title):
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": job_url,
                    "source": "company",
                    "location": item.get("city") or item.get("location"),
                }
            )
        return source_ok(company, url, jobs, started, scanned=len(seen))
    except Exception as error:  # noqa: BLE001
        return source_failed(company, url, error, started)


def collect_wp_rest(company: str, endpoint: str) -> SourceResult:
    started = time.perf_counter()
    try:
        payload = fetch_json(endpoint)
        items = payload if isinstance(payload, list) else []
        jobs: list[dict[str, Any]] = []
        for item in items:
            title_obj = item.get("title") or {}
            rendered = title_obj.get("rendered") if isinstance(title_obj, dict) else title_obj
            title = re.sub(r"<[^>]+>", "", str(rendered or "")).strip()
            title = html_lib.unescape(title)
            job_url = str(item.get("link") or "")
            if not is_ios_job(title) or not job_url:
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": job_url,
                    "source": "company",
                    "source_job_id": item.get("id"),
                }
            )
        return source_ok(company, endpoint, jobs, started, scanned=len(items))
    except Exception as error:  # noqa: BLE001
        return source_failed(company, endpoint, error, started)


def collect_breezy(company: str, portal_host: str) -> SourceResult:
    started = time.perf_counter()
    url = f"https://{portal_host}/"
    try:
        from bs4 import BeautifulSoup

        html = fetch_text(url)
        document = BeautifulSoup(html, "lxml")
        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()
        for anchor in document.select("li.position a[href^='/p/']"):
            absolute = urljoin(url, anchor.get("href") or "")
            if absolute in seen:
                continue
            seen.add(absolute)
            heading = anchor.select_one("h2")
            title = heading.get_text(strip=True) if heading else ""
            if not title:
                title = title_from_slug(absolute)
            if not is_ios_job(title):
                continue
            jobs.append({"company": company, "title": title, "url": absolute, "source": "company"})
        return source_ok(company, url, jobs, started, scanned=len(seen))
    except Exception as error:  # noqa: BLE001
        return source_failed(company, url, error, started)


def title_from_slug(value: str) -> str:
    path = value.split("?", 1)[0]
    slug = [part for part in path.split("/") if part]
    if not slug:
        return value
    return slug[-1].replace("-", " ").replace("_", " ").strip()


def absolute_url(href: str, base_url: str) -> str:
    trimmed = href.strip()
    if trimmed.startswith("http://") or trimmed.startswith("https://"):
        return trimmed
    return urljoin(base_url, trimmed)


def collect_html_regex(
    company: str,
    list_url: str,
    base_url: str,
    pattern: str,
    *,
    url_group: int = 0,
    title_group: int | None = None,
    use_list_url_as_job_url: bool = False,
    allow_bot_wall: bool = False,
) -> SourceResult:
    started = time.perf_counter()
    try:
        if allow_bot_wall:
            html = fetch_text_allowing_bot_wall(list_url)
            if html is None:
                return source_ok(company, list_url, [], started, scanned=0)
        else:
            html = fetch_text(list_url)

        regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()
        for match in regex.finditer(html):
            group_count = len(match.groups())
            if title_group is not None and title_group <= group_count:
                title = (match.group(title_group) or "").strip()
            elif url_group <= group_count:
                title = title_from_slug(match.group(url_group) or "")
            else:
                continue
            if not title:
                continue

            if use_list_url_as_job_url:
                job_url = list_url
                dedupe_key = title
            else:
                if url_group > group_count:
                    continue
                job_url = absolute_url(match.group(url_group) or "", base_url)
                dedupe_key = job_url

            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            if not is_ios_job(title):
                continue
            jobs.append({"company": company, "title": title, "url": job_url, "source": "company"})
        return source_ok(company, list_url, jobs, started, scanned=len(seen))
    except Exception as error:  # noqa: BLE001
        return source_failed(company, list_url, error, started)


def collect_soup_links(
    company: str,
    list_url: str,
    *,
    base_url: str,
    selector: str,
    title_selector: str | None = None,
    location_selector: str | None = None,
    href_contains: str | None = None,
    skip_hrefs: set[str] | None = None,
    skip_exact: set[str] | None = None,
    title_transform: Callable[[str], str] | None = None,
    pagination_selector: str | None = None,
    max_pages: int = 20,
) -> SourceResult:
    started = time.perf_counter()
    try:
        from bs4 import BeautifulSoup

        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()
        skip_hrefs = skip_hrefs or set()
        skip_exact = skip_exact or set()

        pending: list[str] = [list_url]
        visited: set[str] = set()
        while pending:
            page_url = pending.pop(0)
            if page_url in visited or len(visited) >= max_pages:
                continue
            visited.add(page_url)
            html = fetch_text(page_url)
            document = BeautifulSoup(html, "lxml")

            if pagination_selector:
                for link in document.select(pagination_selector):
                    href = (link.get("href") or "").strip()
                    if not href:
                        continue
                    candidate = absolute_url(href, base_url)
                    if candidate not in visited and candidate not in pending:
                        pending.append(candidate)

            for anchor in document.select(selector):
                href = (anchor.get("href") or "").strip()
                if not href:
                    continue
                if href_contains and href_contains not in href:
                    continue
                absolute = absolute_url(href, base_url)
                if absolute in skip_exact or href in skip_exact:
                    continue
                if any(absolute.rstrip("/").endswith(skip.rstrip("/")) for skip in skip_hrefs):
                    continue
                if absolute in seen:
                    continue
                seen.add(absolute)

                title = ""
                if title_selector:
                    node = anchor.select_one(title_selector)
                    if node:
                        title = node.get_text(" ", strip=True)
                if not title:
                    title = anchor.get_text(" ", strip=True)
                if not title:
                    title = title_from_slug(absolute)
                if title_transform:
                    title = title_transform(title)
                if not is_ios_job(title):
                    continue

                location = None
                if location_selector:
                    node = anchor.select_one(location_selector)
                    if node:
                        location = node.get_text(" ", strip=True) or None

                job = {"company": company, "title": title, "url": absolute, "source": "company"}
                if location:
                    job["location"] = location
                jobs.append(job)

        return source_ok(company, list_url, jobs, started, scanned=len(seen))
    except Exception as error:  # noqa: BLE001
        return source_failed(company, list_url, error, started)


def collect_recruitee(company: str, account_slug: str) -> SourceResult:
    started = time.perf_counter()
    url = f"https://{account_slug}.recruitee.com/api/offers/"
    try:
        payload = fetch_json(url)
        offers = payload.get("offers", []) if isinstance(payload, dict) else []
        jobs: list[dict[str, Any]] = []
        for offer in offers:
            title = str(offer.get("title") or "")
            job_url = str(offer.get("careers_url") or offer.get("careers_apply_url") or "")
            if not is_ios_job(title) or not job_url:
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": job_url,
                    "source": "company",
                    "source_job_id": str(offer.get("id")) if offer.get("id") else None,
                    "location": offer.get("location"),
                }
            )
        return source_ok(company, url, jobs, started, scanned=len(offers))
    except Exception as error:  # noqa: BLE001
        return source_failed(company, url, error, started)


def collect_smartrecruiters(company: str, account_slug: str) -> SourceResult:
    started = time.perf_counter()
    base = f"https://api.smartrecruiters.com/v1/companies/{account_slug}/postings"
    try:
        jobs: list[dict[str, Any]] = []
        scanned = 0
        offset = 0
        limit = 100
        while offset < 1000:
            payload = fetch_json(f"{base}?limit={limit}&offset={offset}")
            postings = payload.get("content", []) if isinstance(payload, dict) else []
            if not postings:
                break
            scanned += len(postings)
            for posting in postings:
                title = str(posting.get("name") or "")
                posting_id = posting.get("id")
                if not is_ios_job(title) or not posting_id:
                    continue
                location = posting.get("location") or {}
                parts = [
                    str(location.get(key))
                    for key in ("city", "country")
                    if isinstance(location, dict) and location.get(key)
                ]
                jobs.append(
                    {
                        "company": company,
                        "title": title,
                        "url": f"https://jobs.smartrecruiters.com/{account_slug}/{posting_id}",
                        "source": "company",
                        "source_job_id": str(posting_id),
                        "location": ", ".join(parts) or None,
                    }
                )
            total = int(payload.get("totalFound", 0) or 0)
            offset += limit
            if offset >= total:
                break
        return source_ok(company, base, jobs, started, scanned=scanned)
    except Exception as error:  # noqa: BLE001
        return source_failed(company, base, error, started)
