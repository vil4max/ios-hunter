from __future__ import annotations

import re
import time
from typing import Any

import requests

_DEFAULT_TIMEOUT = 30
_MAX_ATTEMPTS = 3
# Cloudflare challenge HTML is typically ~5–15 KiB; keep a high ceiling so
# long vacancy pages that merely mention a vendor are not false positives.
_BOT_WALL_MAX_LENGTH = 24_000
_BOT_WALL_MARKERS = re.compile(
    r"(?i)("
    r"_Incapsula_Resource|"
    r"Attention Required! \| Cloudflare|"
    r"cf-browser-verification|"
    r"cf_chl_opt|"
    r"Just a moment\.\.\.|"
    r"Checking your browser before accessing|"
    r"Request unsuccessful\. Incapsula incident ID"
    r")"
)


class BotWallError(RuntimeError):
    """Raised when a response is an anti-bot challenge rather than real content."""
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
_DEFAULT_HEADERS = {
    "User-Agent": _BROWSER_UA,
    "Accept": "application/json, text/html, */*",
}


def _merge_headers(extra: dict[str, str] | None) -> dict[str, str]:
    headers = dict(_DEFAULT_HEADERS)
    if extra:
        headers.update(extra)
    return headers


def _get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> requests.Response:
    merged = _merge_headers(headers)
    last_attempt = _MAX_ATTEMPTS - 1
    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = requests.get(url, headers=merged, timeout=timeout)
            if response.status_code < 500 or attempt == last_attempt:
                response.raise_for_status()
                return response
        except requests.HTTPError as error:
            status = error.response.status_code if error.response is not None else 0
            if not (500 <= status <= 599) or attempt == last_attempt:
                raise
        except requests.RequestException:
            if attempt == last_attempt:
                raise
        time.sleep(0.4 * (attempt + 1))
    raise RuntimeError(f"unreachable retry loop for {url}")  # pragma: no cover


def looks_like_bot_wall(text: str) -> bool:
    if len(text) > _BOT_WALL_MAX_LENGTH:
        return False
    return bool(_BOT_WALL_MARKERS.search(text))


def fetch_text(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    text = _get(url, headers=headers, timeout=timeout).text
    if looks_like_bot_wall(text):
        raise BotWallError(f"anti-bot challenge returned instead of content: {url}")
    return text


def fetch_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> Any:
    return _get(url, headers=headers, timeout=timeout).json()


def fetch_text_allowing_bot_wall(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str | None:
    try:
        return fetch_text(url, headers=headers, timeout=timeout)
    except BotWallError:
        return None
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 403:
            return None
        raise


def post_form(url: str, form: dict[str, str], timeout: int = _DEFAULT_TIMEOUT) -> None:
    response = requests.post(
        url,
        data=form,
        headers=_merge_headers(None),
        timeout=timeout,
    )
    response.raise_for_status()


def post_form_data(
    url: str,
    form: dict[str, str],
    *,
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    response = requests.post(
        url,
        data=form,
        headers=_merge_headers(headers),
        timeout=timeout,
    )
    response.raise_for_status()
    return response.text
