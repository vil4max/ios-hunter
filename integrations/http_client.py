from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any


def open_url(request: urllib.request.Request, timeout: int = 30) -> Any:
    context = ssl.create_default_context()
    return urllib.request.urlopen(request, timeout=timeout, context=context)


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with open_url(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_form(url: str, form: dict[str, str], timeout: int = 30) -> None:
    import urllib.parse

    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(form).encode("utf-8"),
        method="POST",
    )
    try:
        with open_url(request, timeout=timeout) as response:
            if response.status >= 300:
                raise RuntimeError(f"HTTP {response.status}")
    except urllib.error.URLError as error:
        raise RuntimeError(f"HTTP request failed: {error}") from error
