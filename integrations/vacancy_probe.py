from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import urlsplit

import requests

from integrations.http_client import _merge_headers, looks_like_bot_wall

_SOFT_404_MARKERS = (
    "page not found",
    "vacancy not found",
    "job not found",
    "position is no longer",
    "no longer available",
    "this job has been filled",
    "вакансия не найдена",
    "вакансию закрыли",
    "вакансия закрыта",
    "вакансію закрили",
    "вакансія закрита",
    "объявление снято",
    "оголошення знято",
)

_PLATFORM_CLOSED_MARKERS = (
    "vacancy is closed",
    "job is closed",
    "this vacancy is no longer",
    "вакансию закрыли",
    "вакансію закрили",
)

_ROLE_KEYWORDS = frozenset(
    {
        "ios",
        "swift",
        "swiftui",
        "mobile",
        "macos",
        "iphone",
        "ipad",
        "uikit",
    }
)

_JOB_TITLE_MARKERS = (
    "developer",
    "engineer",
    "розробник",
    "інженер",
    "программист",
    "lead",
    "architect",
)

_SKIP_HOST_SUFFIXES = (
    "t.me",
    "telegram.me",
    "telegram.org",
)

_SKIP_PATH_PREFIXES = (
    "/my/",
    "/login",
)


@dataclass(frozen=True)
class ProbeResult:
    url: str
    closed: bool
    skipped: bool
    http_status: int | None
    reason: str
    page_title: str = ""


def _host(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def should_skip_url(url: str) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return "no url"
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"}:
        return "non-http url"
    host = _host(raw)
    for suffix in _SKIP_HOST_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            return f"skip host {host}"
    path = parts.path or ""
    if host.endswith("djinni.co") and any(path.startswith(prefix) for prefix in _SKIP_PATH_PREFIXES):
        return "private djinni url"
    return None


def _strip_tags(value: str) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", value)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return unescape(re.sub(r"\s+", " ", text)).strip()


def _extract_title(html: str) -> str:
    for pattern in (
        r"(?is)<h1[^>]*>(.*?)</h1>",
        r"(?is)<title[^>]*>(.*?)</title>",
    ):
        match = re.search(pattern, html)
        if not match:
            continue
        title = _strip_tags(match.group(1))
        if title:
            return title[:200]
    return ""


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Zа-яА-ЯіїєґІЇЄҐ0-9+]{3,}", value.lower())
        if token not in {"the", "and", "для", "вакансія", "vacancy", "job", "developer", "engineer"}
    }


def _role_keyword_mismatch(card_title: str, page_title: str) -> bool:
    card = (card_title or "").strip().lower()
    page = (page_title or "").strip().lower()
    if not card or not page:
        return False
    if not any(marker in page for marker in _JOB_TITLE_MARKERS):
        return False
    card_roles = {word for word in _ROLE_KEYWORDS if word in card}
    if not card_roles:
        return False
    page_roles = {word for word in _ROLE_KEYWORDS if word in page}
    if page_roles & card_roles:
        return False
    card_tokens = _tokens(card)
    page_tokens = _tokens(page)
    if not card_tokens or not page_tokens:
        return False
    overlap = card_tokens & page_tokens
    return len(overlap) / len(card_tokens | page_tokens) < 0.2


def _huntflow_archived(html: str) -> bool | None:
    match = re.search(
        r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    )
    if not match:
        return None
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    for item in payload:
        if not isinstance(item, dict):
            continue
        if "is_archived" not in item:
            continue
        archived_ref = item.get("is_archived")
        if isinstance(archived_ref, bool):
            return archived_ref
        if isinstance(archived_ref, int) and 0 <= archived_ref < len(payload):
            value = payload[archived_ref]
            if isinstance(value, bool):
                return value
    return None


def _body_closed(html: str) -> str | None:
    low = html.lower()
    for marker in _SOFT_404_MARKERS:
        if marker in low:
            return f"soft-404: {marker}"
    for marker in _PLATFORM_CLOSED_MARKERS:
        if marker in low:
            return f"platform closed: {marker}"
    archived = _huntflow_archived(html)
    if archived is True:
        return "huntflow archived"
    return None


def _response_is_bot_blocked(response: requests.Response) -> bool:
    mitigated = str(response.headers.get("cf-mitigated") or "").strip().lower()
    if mitigated in {"challenge", "managed_challenge", "js_challenge"}:
        return True
    return looks_like_bot_wall(response.text or "")


def _zone3000_slug(url: str) -> str:
    path = urlsplit(url).path or ""
    return path.rstrip("/").rsplit("/", 1)[-1].strip()


def _probe_zone3000_api(
    url: str,
    *,
    http_status: int | None,
    session: requests.Session,
    timeout: int,
) -> ProbeResult | None:
    """Confirm ZONE3000 vacancies via JSON API when HTML is blocked or 404.

    ZONE3000 sits behind Cloudflare; GitHub runners often get challenge/404 HTML
    for pages that still open in a browser. The public API lists active slugs.
    """
    if _host(url) != "zone3000.net":
        return None
    slug = _zone3000_slug(url)
    if not slug:
        return None
    api_url = "https://zone3000.net/api/vacancies"
    try:
        response = session.get(
            api_url,
            headers=_merge_headers(
                {
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://zone3000.net/vacancies",
                }
            ),
            timeout=timeout,
            allow_redirects=True,
        )
    except requests.RequestException as error:
        return ProbeResult(
            url=url,
            closed=False,
            skipped=True,
            http_status=http_status,
            reason=f"zone3000 api error: {type(error).__name__}",
        )

    api_status = int(response.status_code)
    if _response_is_bot_blocked(response) or api_status >= 400:
        return ProbeResult(
            url=url,
            closed=False,
            skipped=True,
            http_status=http_status if http_status is not None else api_status,
            reason=f"zone3000 api blocked ({api_status})",
        )

    try:
        payload: Any = response.json()
    except ValueError:
        return ProbeResult(
            url=url,
            closed=False,
            skipped=True,
            http_status=http_status,
            reason="zone3000 api invalid json",
        )
    items = payload if isinstance(payload, list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_slug = str(item.get("url") or "").strip().lstrip("/")
        if item_slug == slug:
            title = str(item.get("title") or "").strip()
            return ProbeResult(
                url=url,
                closed=False,
                skipped=False,
                http_status=http_status if http_status is not None else 200,
                reason="open (zone3000 api)",
                page_title=title[:200],
            )
    return ProbeResult(
        url=url,
        closed=True,
        skipped=False,
        http_status=http_status if http_status is not None else api_status,
        reason="zone3000 api: vacancy missing",
    )


def probe_vacancy_url(
    url: str,
    *,
    card_title: str = "",
    timeout: int = 25,
    session: requests.Session | None = None,
) -> ProbeResult:
    skip = should_skip_url(url)
    if skip:
        return ProbeResult(
            url=url,
            closed=False,
            skipped=True,
            http_status=None,
            reason=skip,
        )

    http = session or requests.Session()
    try:
        response = http.get(
            url,
            headers=_merge_headers(None),
            timeout=timeout,
            allow_redirects=True,
        )
    except requests.RequestException as error:
        return ProbeResult(
            url=url,
            closed=False,
            skipped=True,
            http_status=None,
            reason=f"request error: {type(error).__name__}",
        )

    status = int(response.status_code)
    final_url = str(response.url or url)
    html = response.text or ""
    page_title = _extract_title(html)

    if _response_is_bot_blocked(response):
        api_result = _probe_zone3000_api(
            url,
            http_status=status,
            session=http,
            timeout=timeout,
        )
        if api_result is not None:
            return api_result
        return ProbeResult(
            url=final_url,
            closed=False,
            skipped=True,
            http_status=status,
            reason=f"bot wall (http {status})",
        )

    if status in {404, 410}:
        api_result = _probe_zone3000_api(
            url,
            http_status=status,
            session=http,
            timeout=timeout,
        )
        if api_result is not None:
            return api_result
        return ProbeResult(
            url=final_url,
            closed=True,
            skipped=False,
            http_status=status,
            reason=f"http {status}",
            page_title=page_title,
        )
    if status >= 400:
        return ProbeResult(
            url=final_url,
            closed=False,
            skipped=True,
            http_status=status,
            reason=f"http {status}",
        )

    closed_reason = _body_closed(html)
    if closed_reason:
        return ProbeResult(
            url=final_url,
            closed=True,
            skipped=False,
            http_status=status,
            reason=closed_reason,
            page_title=page_title,
        )
    if _role_keyword_mismatch(card_title, page_title):
        return ProbeResult(
            url=final_url,
            closed=True,
            skipped=False,
            http_status=status,
            reason=f"title mismatch: {page_title}",
            page_title=page_title,
        )
    return ProbeResult(
        url=final_url,
        closed=False,
        skipped=False,
        http_status=status,
        reason="open",
        page_title=page_title,
    )
