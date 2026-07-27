from __future__ import annotations

import os

import requests

from integrations.http_client import _merge_headers

TELEGRAM_MAX_LENGTH = 4096


def split_telegram_text(text: str, limit: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        window = remaining[:limit]
        split_at = window.rfind("\n")
        if split_at <= 0:
            split_at = limit
        chunk = remaining[:split_at].rstrip("\n")
        if not chunk:
            chunk = remaining[:limit]
            split_at = limit
        chunks.append(chunk)
        remaining = remaining[split_at:].lstrip("\n")
    return chunks


def _post_message(token: str, chat_id: str, text: str, timeout: int = 30) -> None:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        },
        headers=_merge_headers(None),
        timeout=timeout,
    )
    if response.ok:
        return
    detail = (response.text or "").strip()
    if len(detail) > 500:
        detail = detail[:500] + "…"
    raise requests.HTTPError(
        f"{response.status_code} Client Error for url: {response.url}"
        + (f"; body={detail}" if detail else ""),
        response=response,
    )


def send_message(text: str) -> None:
    token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print(text)
        return

    for chunk in split_telegram_text(text):
        _post_message(token, chat_id, chunk)
