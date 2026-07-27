from __future__ import annotations

import pytest
import requests

from integrations import http_client


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "", payload: object = None) -> None:
        self.status_code = status_code
        self.text = text
        self._payload = payload

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(http_client.time, "sleep", lambda _seconds: None)


def _record_get(monkeypatch: pytest.MonkeyPatch, responses: list[object]) -> list[dict]:
    calls: list[dict] = []

    def fake_get(url: str, headers: dict, timeout: int) -> FakeResponse:
        calls.append({"url": url, "headers": headers, "timeout": timeout})
        item = responses[min(len(calls) - 1, len(responses) - 1)]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(http_client.requests, "get", fake_get)
    return calls


def test_fetch_text_returns_body_and_sends_browser_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _record_get(monkeypatch, [FakeResponse(text="<html>ok</html>")])

    assert http_client.fetch_text("https://example.com") == "<html>ok</html>"
    assert "Mozilla/5.0" in calls[0]["headers"]["User-Agent"]
    assert calls[0]["timeout"] == 30


def test_fetch_text_merges_extra_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _record_get(monkeypatch, [FakeResponse(text="ok")])

    http_client.fetch_text("https://example.com", headers={"Accept": "text/html", "X-Test": "1"})

    assert calls[0]["headers"]["Accept"] == "text/html"
    assert calls[0]["headers"]["X-Test"] == "1"
    assert "Mozilla/5.0" in calls[0]["headers"]["User-Agent"]


def test_fetch_json_parses_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    _record_get(monkeypatch, [FakeResponse(payload={"jobs": [1, 2]})])

    assert http_client.fetch_json("https://example.com") == {"jobs": [1, 2]}


def test_get_retries_on_server_error_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _record_get(
        monkeypatch,
        [FakeResponse(status_code=503), FakeResponse(status_code=503), FakeResponse(text="late")],
    )

    assert http_client.fetch_text("https://example.com") == "late"
    assert len(calls) == 3


def test_get_raises_after_exhausting_server_error_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _record_get(monkeypatch, [FakeResponse(status_code=500)])

    with pytest.raises(requests.HTTPError):
        http_client.fetch_text("https://example.com")
    assert len(calls) == 3


def test_get_does_not_retry_client_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _record_get(monkeypatch, [FakeResponse(status_code=404)])

    with pytest.raises(requests.HTTPError):
        http_client.fetch_text("https://example.com")
    assert len(calls) == 1


def test_get_retries_connection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _record_get(
        monkeypatch,
        [requests.ConnectionError("boom"), requests.ConnectionError("boom"), FakeResponse(text="ok")],
    )

    assert http_client.fetch_text("https://example.com") == "ok"
    assert len(calls) == 3


def test_get_reraises_connection_error_after_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    _record_get(monkeypatch, [requests.ConnectionError("boom")])

    with pytest.raises(requests.ConnectionError):
        http_client.fetch_text("https://example.com")


@pytest.mark.parametrize(
    "body",
    [
        '<html><script src="/_Incapsula_Resource?SWJIYLWA=x"></script></html>',
        "<html><title>Just a moment...</title></html>",
        "<html>Checking your browser before accessing example.com</html>",
        "<html><title>Attention Required! | Cloudflare</title></html>",
    ],
)
def test_fetch_text_rejects_bot_walls(monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    _record_get(monkeypatch, [FakeResponse(text=body)])

    with pytest.raises(http_client.BotWallError):
        http_client.fetch_text("https://example.com")


def test_long_page_mentioning_cloudflare_is_not_a_bot_wall(monkeypatch: pytest.MonkeyPatch) -> None:
    body = "Just a moment..." + ("x" * 5000)
    _record_get(monkeypatch, [FakeResponse(text=body)])

    assert http_client.fetch_text("https://example.com") == body


def test_fetch_text_allowing_bot_wall_returns_none_on_403(monkeypatch: pytest.MonkeyPatch) -> None:
    _record_get(monkeypatch, [FakeResponse(status_code=403)])

    assert http_client.fetch_text_allowing_bot_wall("https://example.com") is None


def test_fetch_text_allowing_bot_wall_returns_none_on_challenge(monkeypatch: pytest.MonkeyPatch) -> None:
    _record_get(monkeypatch, [FakeResponse(text="<html>Just a moment...</html>")])

    assert http_client.fetch_text_allowing_bot_wall("https://example.com") is None


def test_fetch_text_allowing_bot_wall_reraises_other_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _record_get(monkeypatch, [FakeResponse(status_code=404)])

    with pytest.raises(requests.HTTPError):
        http_client.fetch_text_allowing_bot_wall("https://example.com")


def test_fetch_text_allowing_bot_wall_returns_body(monkeypatch: pytest.MonkeyPatch) -> None:
    _record_get(monkeypatch, [FakeResponse(text="fine")])

    assert http_client.fetch_text_allowing_bot_wall("https://example.com") == "fine"


def test_post_form_raises_for_status(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_post(url: str, data: dict, headers: dict, timeout: int) -> FakeResponse:
        captured.update({"url": url, "data": data, "headers": headers})
        return FakeResponse(status_code=500)

    monkeypatch.setattr(http_client.requests, "post", fake_post)

    with pytest.raises(requests.HTTPError):
        http_client.post_form("https://example.com", {"a": "b"})
    assert captured["data"] == {"a": "b"}


def test_post_form_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        http_client.requests,
        "post",
        lambda url, data, headers, timeout: FakeResponse(text=""),
    )

    assert http_client.post_form("https://example.com", {"a": "b"}) is None


def test_post_form_data_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_post(url: str, data: dict, headers: dict, timeout: int) -> FakeResponse:
        captured.update({"headers": headers})
        return FakeResponse(text="payload")

    monkeypatch.setattr(http_client.requests, "post", fake_post)

    assert http_client.post_form_data("https://example.com", {"a": "b"}, headers={"X": "1"}) == "payload"
    assert captured["headers"]["X"] == "1"


def test_looks_like_bot_wall_on_clean_page() -> None:
    assert http_client.looks_like_bot_wall("<html><body>jobs</body></html>") is False
