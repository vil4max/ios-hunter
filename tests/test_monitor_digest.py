from __future__ import annotations

from collector.types import SourceResult
from integrations import monitor_digest
from integrations.monitor_digest import render_monitor_digest, send_monitor_digest
from parser.activity import ActivitySummary
from tests.conftest import make_job_record, make_vacancy


def test_render_monitor_digest_includes_activity_and_counts() -> None:
    activity = ActivitySummary(new=2, updated=1, closed=3)
    results = [
        SourceResult("a", "Alpha", "https://a", [], "healthy", None, 100),
        SourceResult("b", "Beta", "https://b", [], "healthy", None, 120),
    ]

    message = render_monitor_digest(activity, open_roles=15, tracked_total=40, source_results=results)

    assert "✅ iOS Hunter" in message
    assert "Actionable: 3" in message
    assert "New: 2" in message
    assert "Open roles now: 15" in message
    assert "Tracking in total: 40" in message
    assert "Sources: 2/2 OK" in message
    assert "Checked" in message
    assert "Kyiv" in message


def test_render_monitor_digest_shows_failed_sources() -> None:
    activity = ActivitySummary()
    results = [
        SourceResult("a", "Alpha", "https://a", [], "healthy", None, 100),
        SourceResult("b", "Beta", "https://b", [], "failed", "timeout", 0),
    ]

    message = render_monitor_digest(activity, open_roles=0, tracked_total=0, source_results=results)

    assert "Sources: 1/2 OK (1 failed)" in message


def test_send_monitor_digest_skips_when_telegram_disabled(repo, monkeypatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr(monitor_digest, "send_message", lambda text: sent.append(text))

    vacancy = make_vacancy()
    repo.upsert_job(make_job_record(vacancy))

    result = send_monitor_digest(
        repo,
        ActivitySummary(),
        [SourceResult("a", "Alpha", "https://a", [], "healthy", None, 100)],
        {"telegram": {"enabled": False}},
    )

    assert result is False
    assert sent == []


def test_send_monitor_digest_sends_when_enabled(repo, monkeypatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr(monitor_digest, "send_message", lambda text: sent.append(text))

    open_job = make_job_record(make_vacancy(title="Senior iOS Developer", url="https://example.com/open"))
    closed_job = make_job_record(
        make_vacancy(title="Staff iOS Engineer", url="https://example.com/closed"),
        status="closed",
    )
    repo.upsert_job(open_job)
    repo.upsert_job(closed_job)

    result = send_monitor_digest(
        repo,
        ActivitySummary(new=1),
        [SourceResult("a", "Alpha", "https://a", [], "healthy", None, 100)],
        {"telegram": {"enabled": True}},
    )

    assert result is True
    assert len(sent) == 1
    assert "Open roles now: 1" in sent[0]
    assert "Tracking in total: 2" in sent[0]
