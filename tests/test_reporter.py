from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from integrations.notify import CollectReportStats
from integrations.telegram import TELEGRAM_MAX_LENGTH
from planner.plan import DailyPlan, ProjectCard
from project_sync.sync import SyncItemResult, SyncResult
from reporter.daily import format_daily_dashboard
from reporter.hourly import (
    _pack_vacancy_batches,
    format_hourly_heartbeat,
    format_hourly_new_vacancies,
    notify_hourly_inbox,
    vacancies_for_alert,
)
from tests.conftest import make_vacancy

_KYIV = ZoneInfo("Europe/Kyiv")


def test_hourly_lists_new_vacancies_only() -> None:
    now = datetime(2026, 7, 15, 11, 0, tzinfo=_KYIV)
    stats = CollectReportStats(
        found=10,
        seen_total=8,
        new_count=2,
        duplicates_removed=1,
        failed_source_names=(),
        sites_ok=10,
        sites_total=10,
        telegram_ok=3,
        telegram_total=3,
        telegram_ok_names=("itrecruit_ua", "remotejobss", "itfreelancers"),
    )
    vacancies = [
        make_vacancy(
            title="Senior iOS Engineer",
            company="Acme",
            url="https://example.com/a",
            source="company",
            description="SwiftUI and UIKit experience required",
            location="Kyiv, Ukraine",
            remote="remote",
        ),
        make_vacancy(
            title="Swift Developer",
            company="Beta",
            url="https://example.com/b",
            source="company",
            description=None,
            location=None,
            remote=None,
        ),
    ]
    message = format_hourly_new_vacancies(
        vacancies,
        stats=stats,
        board_url="https://github.com/users/acme/projects/1",
        now=now,
    )
    assert message == (
        "🆕 +2\n"
        "\n"
        "1. Acme — Senior iOS Engineer\n"
        "   https://example.com/a\n"
        "2. Beta — Swift Developer\n"
        "   https://example.com/b\n"
        "\n"
        "📊 10 найдено · 2 новых · 2026-07-15 11:00\n"
        "🔗 https://github.com/users/acme/projects/1"
    )


def test_hourly_telegram_vacancy_is_compact() -> None:
    now = datetime(2026, 7, 15, 11, 0, tzinfo=_KYIV)
    published = datetime(2026, 7, 22, 12, 44, tzinfo=_KYIV)
    stats = CollectReportStats(
        found=1,
        seen_total=0,
        new_count=1,
        duplicates_removed=0,
        failed_source_names=(),
    )
    vacancy = make_vacancy(
        title="Senior iOS Engineer",
        company="SmartTek Solutions",
        url="https://t.me/itrecruit_ua/123",
        source="telegram",
        description="Swift, UIKit, 5+ years · Remote UA",
        published_at=published,
    )
    message = format_hourly_new_vacancies(
        [vacancy],
        stats=stats,
        board_url="https://board",
        now=now,
    )
    assert message == (
        "🆕 +1\n"
        "\n"
        "1. SmartTek Solutions — Senior iOS Engineer\n"
        "   https://t.me/itrecruit_ua/123\n"
        "\n"
        "📊 1 найдено · 1 новых · 2026-07-15 11:00\n"
        "🔗 https://board"
    )
    assert "📝" not in message
    assert "📅" not in message
    assert "📡" not in message


def test_hourly_heartbeat_when_no_new() -> None:
    now = datetime(2026, 7, 15, 11, 0, tzinfo=_KYIV)
    stats = CollectReportStats(
        found=22,
        seen_total=40,
        new_count=0,
        duplicates_removed=0,
        failed_source_names=(),
        sites_ok=12,
        sites_total=12,
        telegram_ok=3,
        telegram_total=3,
        telegram_ok_names=("itrecruit_ua", "remotejobss", "itfreelancers"),
    )
    live = [
        make_vacancy(company="EPAM", url="https://example.com/epam/1"),
        make_vacancy(company="EPAM", url="https://example.com/epam/2"),
        make_vacancy(company="EPAM", url="https://example.com/epam/3"),
        make_vacancy(company="DataArt", url="https://example.com/dataart/1"),
        make_vacancy(company="DataArt", url="https://example.com/dataart/2"),
    ]
    message = format_hourly_heartbeat(
        stats=stats,
        new_count=0,
        board_url="https://board",
        now=now,
        live=live,
    )
    assert message == (
        "📭 Нет новых\n"
        "\n"
        "Живые: 5 · 2 компаний\n"
        "\n"
        "📊 22 найдено · 0 новых · 2026-07-15 11:00"
    )


def test_hourly_heartbeat_reports_partial_failures() -> None:
    now = datetime(2026, 7, 15, 11, 0, tzinfo=_KYIV)
    stats = CollectReportStats(
        found=20,
        seen_total=40,
        new_count=0,
        duplicates_removed=0,
        failed_source_names=("SoftServe", "Telegram @remotejobss"),
        sites_ok=11,
        sites_total=12,
        telegram_ok=2,
        telegram_total=3,
        telegram_ok_names=("itrecruit_ua", "itfreelancers"),
    )
    message = format_hourly_heartbeat(stats=stats, now=now)
    assert "⚠️ Поиск по сайтам: 11/12 ошибки — SoftServe" in message
    assert "⚠️ Telegram: 2/3 ошибки" in message
    assert "@remotejobss" not in message
    assert "📊 20 найдено · 0 новых · 2026-07-15 11:00" in message


def test_hourly_heartbeat_shows_only_degraded_without_ok_noise() -> None:
    now = datetime(2026, 7, 27, 22, 39, tzinfo=_KYIV)
    stats = CollectReportStats(
        found=31,
        seen_total=50,
        new_count=0,
        duplicates_removed=0,
        failed_source_names=(),
        sites_ok=54,
        sites_total=55,
        telegram_ok=3,
        telegram_total=3,
        degraded_source_names=("Binary Studio",),
    )
    live = [
        make_vacancy(company="Intellias", url="https://example.com/1"),
        make_vacancy(company="Intellias", url="https://example.com/2"),
        make_vacancy(company="N-iX", url="https://example.com/3"),
    ]
    message = format_hourly_heartbeat(stats=stats, now=now, live=live)
    assert message == (
        "📭 Нет новых\n"
        "\n"
        "Живые: 3 · 2 компаний\n"
        "\n"
        "🔕 Источники без результата: 1 — Binary Studio\n"
        "📊 31 найдено · 0 новых · 2026-07-27 22:39"
    )
    assert "✅ Поиск по сайтам" not in message
    assert "✅ Telegram" not in message


def test_vacancies_for_alert_prefers_created_sync_items() -> None:
    fresh = [
        make_vacancy(url="https://example.com/1", title="A", company="Acme"),
        make_vacancy(url="https://example.com/2", title="B", company="Beta"),
    ]
    sync = SyncResult(
        created=[
            SyncItemResult(
                canonical_url="https://example.com/1",
                company="Acme",
                title="A",
                created=True,
            )
        ]
    )
    shown = vacancies_for_alert(sync, fresh)
    assert len(shown) == 1
    assert shown[0].url == "https://example.com/1"


def test_vacancies_for_alert_includes_existing_fresh_for_retry() -> None:
    fresh = [
        make_vacancy(url="https://example.com/1", title="A", company="Acme"),
        make_vacancy(url="https://example.com/2", title="B", company="Beta"),
    ]
    sync = SyncResult(
        existing=[
            SyncItemResult(
                canonical_url="https://example.com/1",
                company="Acme",
                title="A",
                existing=True,
            )
        ]
    )
    shown = vacancies_for_alert(sync, fresh)
    assert len(shown) == 1
    assert shown[0].url == "https://example.com/1"


def test_pack_vacancy_batches_splits_long_lists() -> None:
    stats = CollectReportStats(found=30, seen_total=0, new_count=30, duplicates_removed=0)
    vacancies = [
        make_vacancy(
            title=f"Senior iOS Engineer {index}",
            company=f"Company {index}",
            url=f"https://example.com/jobs/{index}",
            source="company",
        )
        for index in range(1, 25)
    ]
    messages = _pack_vacancy_batches(
        vacancies,
        stats=stats,
        board_url="https://board",
        limit=400,
    )
    assert len(messages) >= 2
    assert all(len(message) <= TELEGRAM_MAX_LENGTH for message in messages)
    assert messages[0].startswith("🆕 +24 (1/")
    assert "1. Company 1 — Senior iOS Engineer 1" in messages[0]
    assert any(
        f"{len(vacancies)}. Company {len(vacancies)} — Senior iOS Engineer {len(vacancies)}" in message
        for message in messages
    )


def test_notify_hourly_inbox_sends_packed_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr("reporter.hourly.send_message", sent.append)
    monkeypatch.setattr("reporter.hourly.TELEGRAM_MAX_LENGTH", 350)
    stats = CollectReportStats(found=20, seen_total=0, new_count=20, duplicates_removed=0)
    vacancies = [
        make_vacancy(
            title=f"Role {index}",
            company=f"Co {index}",
            url=f"https://example.com/{index}",
        )
        for index in range(1, 21)
    ]
    sync = SyncResult(
        created=[
            SyncItemResult(
                canonical_url=vacancy.url,
                company=vacancy.company,
                title=vacancy.title,
                created=True,
            )
            for vacancy in vacancies
        ]
    )
    assert notify_hourly_inbox(sync, vacancies, stats=stats, board_url="https://board") is True
    assert len(sent) >= 2
    assert all(len(message) <= 350 for message in sent)


def test_daily_dashboard_formatter_still_works() -> None:
    card = ProjectCard(
        item_id="1",
        issue_number=3,
        title="iOS Engineer",
        url="https://example.com/job",
        issue_url="https://github.com/a/b/issues/3",
        company="Acme",
        source="test",
        canonical_url="https://example.com/job",
        status="Inbox",
        priority="P1",
        offer_probability="",
        follow_up=None,
        applied_at=None,
        created_at=None,
        updated_at=None,
    )
    plan = DailyPlan(
        today_tasks=[card],
        new_vacancies=[card],
        needs_attention=[],
        pending_follow_ups=[],
        upcoming_interviews=[],
        status_counts={"Inbox": 1, "Applied": 0},
        cards=[card],
    )
    now = datetime(2026, 7, 15, 7, 0, tzinfo=_KYIV)
    message = format_daily_dashboard(plan, board_url="https://board", now=now)
    assert "Career Agent · 2026-07-15" in message
    assert "Acme — iOS Engineer" in message
