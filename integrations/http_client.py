from __future__ import annotations

import re
import time
from collections.abc import Callable, Sequence
from typing import Any

import requests

_DEFAULT_TIMEOUT = 30
_MAX_ATTEMPTS = 3
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
_IMPERSONATE_CANDIDATES = (
    "chrome136",
    "chrome131",
    "chrome124",
    "safari184",
    "firefox135",
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


def _impersonate_headers(extra: dict[str, str] | None) -> dict[str, str]:
    headers = {"Accept": "application/json, text/html, */*"}
    if extra:
        headers.update(extra)
    headers.pop("User-Agent", None)
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


def fetch_impersonated(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
    warm_urls: Sequence[str] | None = None,
    accept: Callable[[str], bool] | None = None,
) -> str:
    from curl_cffi import requests as curl_requests

    merged = _impersonate_headers(headers)
    last_error: Exception | None = None
    for impersonate in _IMPERSONATE_CANDIDATES:
        try:
            session = curl_requests.Session(impersonate=impersonate)
            warmed = True
            for warm_url in warm_urls or ():
                warm_response = session.get(warm_url, headers=merged, timeout=timeout)
                if warm_response.status_code >= 400:
                    last_error = RuntimeError(
                        f"HTTP {warm_response.status_code} warming {warm_url}"
                    )
                    warmed = False
                    break
            if not warmed:
                continue

            response = session.get(url, headers=merged, timeout=timeout)
            if response.status_code >= 400:
                last_error = RuntimeError(f"HTTP {response.status_code} for {url}")
                continue
            text = response.text or ""
            if looks_like_bot_wall(text):
                last_error = BotWallError(
                    f"anti-bot challenge returned instead of content: {url}"
                )
                continue
            if accept is not None and not accept(text):
                last_error = RuntimeError(f"unexpected payload for {url}")
                continue
            return text
        except Exception as error:  # noqa: BLE001
            last_error = error
    raise RuntimeError(str(last_error) if last_error else f"failed to fetch {url}")


def fetch_text(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    try:
        text = _get(url, headers=headers, timeout=timeout).text
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 403:
            return fetch_impersonated(url, headers=headers, timeout=timeout)
        raise
    if looks_like_bot_wall(text):
        return fetch_impersonated(url, headers=headers, timeout=timeout)
    return text


def fetch_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> Any:
    return _get(url, headers=headers, timeout=timeout).json()


def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> Any:
    response = requests.post(
        url,
        params=params,
        json=payload,
        headers=_merge_headers(headers),
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def fetch_text_allowing_bot_wall(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str | None:
    try:
        text = _get(url, headers=headers, timeout=timeout).text
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 403:
            return None
        raise
    if looks_like_bot_wall(text):
        return None
    return text


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
