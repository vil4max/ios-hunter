from __future__ import annotations

from typing import Any

import requests


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int = 30) -> dict[str, Any]:
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def post_form(url: str, form: dict[str, str], timeout: int = 30) -> None:
    response = requests.post(url, data=form, timeout=timeout)
    response.raise_for_status()


def fetch_json(url: str, timeout: int = 30) -> Any:
    response = requests.get(
        url,
        headers={"User-Agent": "ios-hunter/2.0 (+https://github.com/)"},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
