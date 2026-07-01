from __future__ import annotations

import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

MOBILE_KEYWORDS = ("ios", "swift", "mobile", "android")
MAX_DESCRIPTION_LENGTH = 8000
TIMEOUT = 20


def is_mobile_title(title: str) -> bool:
    lowered = title.lower()
    return any(keyword in lowered for keyword in MOBILE_KEYWORDS)


def fetch_description(url: str) -> str | None:
    try:
        response = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": "ios-hunter/2.0 (+https://github.com/)"},
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    content_type = response.headers.get("Content-Type", "")
    if "json" in content_type:
        return _description_from_json(response.json())

    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    candidates: list[str] = []
    for selector in (
        "article",
        "[class*='description']",
        "[class*='job-description']",
        "[class*='vacancy']",
        "main",
    ):
        for node in soup.select(selector):
            text = node.get_text("\n", strip=True)
            if len(text) > 120:
                candidates.append(text)

    if not candidates:
        text = soup.get_text("\n", strip=True)
        candidates.append(text)

    best = max(candidates, key=len, default="")
    best = re.sub(r"\n{3,}", "\n\n", best).strip()
    if len(best) < 80:
        return None
    return best[:MAX_DESCRIPTION_LENGTH]


def _description_from_json(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("description", "body", "content", "jobDescription"):
        value = payload.get(key)
        if isinstance(value, str) and len(value) > 80:
            return value[:MAX_DESCRIPTION_LENGTH]
        if isinstance(value, dict):
            html = value.get("html") or value.get("text")
            if isinstance(html, str) and len(html) > 80:
                return BeautifulSoup(html, "lxml").get_text("\n", strip=True)[:MAX_DESCRIPTION_LENGTH]
    job = payload.get("job")
    if isinstance(job, dict):
        return _description_from_json(job)
    return None


def should_fetch(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    blocked = ("linkedin.com", "facebook.com")
    return not any(block in host for block in blocked)
