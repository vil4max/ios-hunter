from __future__ import annotations

import pytest
import requests

from integrations import telegram


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "", url: str = "https://api.telegram.org") -> None:
        self.status_code = status_code
        self.text = text
        self.url = url
        self.ok = status_code < 400


def test_split_telegram_text_keeps_short_message() -> None:
    assert telegram.split_telegram_text("hello") == ["hello"]


def test_split_telegram_text_breaks_on_newlines() -> None:
    first = "a" * 100
    second = "b" * 100
    chunks = telegram.split_telegram_text(f"{first}\n{second}", limit=120)
    assert chunks == [first, second]


def test_split_telegram_text_hard_splits_without_newlines() -> None:
    body = "x" * 250
    chunks = telegram.split_telegram_text(body, limit=100)
    assert chunks == ["x" * 100, "x" * 100, "x" * 50]
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_send_message_prints_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    telegram.send_message("ping")
    assert capsys.readouterr().out.strip() == "ping"


def test_send_message_chunks_and_posts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    posts: list[dict] = []

    def fake_post(url: str, data: dict, headers: dict, timeout: int) -> FakeResponse:
        posts.append({"url": url, "data": data, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(telegram.requests, "post", fake_post)
    monkeypatch.setattr(
        telegram,
        "split_telegram_text",
        lambda text, limit=telegram.TELEGRAM_MAX_LENGTH: ["one", "two"],
    )
    telegram.send_message("ignored")
    assert [post["data"]["text"] for post in posts] == ["one", "two"]
    assert posts[0]["data"]["chat_id"] == "42"
    assert "bottoken/sendMessage" in posts[0]["url"]


def test_send_message_includes_error_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")

    def fake_post(url: str, data: dict, headers: dict, timeout: int) -> FakeResponse:
        return FakeResponse(status_code=400, text='{"description":"message is too long"}')

    monkeypatch.setattr(telegram.requests, "post", fake_post)
    with pytest.raises(requests.HTTPError, match="message is too long"):
        telegram.send_message("hello")
