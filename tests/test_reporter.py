from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from integrations.notify import CollectReportStats
from planner.plan import DailyPlan, ProjectCard
from project_sync.sync import SyncItemResult, SyncResult
from reporter.daily import format_daily_dashboard
from reporter.hourly import (
    format_hourly_heartbeat,
    format_hourly_new_vacancies,
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
        ),
        make_vacancy(
            title="Swift Developer",
            company="Beta",
            url="https://example.com/b",
            source="company",
            description=None,
        ),
    ]
    message = format_hourly_new_vacancies(
        vacancies,
        stats=stats,
        board_url="https://github.com/users/acme/projects/1",
        now=now,
    )
    assert message == (
        "🆕 +2 Inbox\n"
        "\n"
        "1. Senior iOS Engineer\n"
        "   📝 SwiftUI and UIKit experience required\n"
        "   🏢 Acme\n"
        "   📡 Acme careers\n"
        "   🔗 https://example.com/a\n"
        "\n"
        "2. Swift Developer\n"
        "   🏢 Beta\n"
        "   📡 Beta careers\n"
        "   🔗 https://example.com/b\n"
        "\n"
        "✅ Поиск по сайтам: OK (10/10)\n"
        "✅ Telegram: OK (3/3) · @itrecruit_ua, @remotejobss, @itfreelancers\n"
        "📊 Найдено: 10 · в базе: 8 · новых: 2\n"
        "\n"
        "✅ Все проверки прошли · 2026-07-15 11:00\n"
        "🔗 https://github.com/users/acme/projects/1"
    )


def test_hourly_telegram_vacancy_uses_snippet_and_date() -> None:
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
    assert "📡" not in message
    assert "Telegram @itrecruit_ua" not in message
    assert "📝 Swift, UIKit, 5+ years · Remote UA" in message
    assert "🏢 SmartTek Solutions" in message
    assert "📅 2026-07-22 12:44" in message
    assert "🔗 https://t.me/itrecruit_ua/123" in message


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
    message = format_hourly_heartbeat(
        stats=stats,
        new_count=0,
        board_url="https://board",
        now=now,
    )
    assert message == (
        "📭 Новых вакансий не обнаружено\n"
        "\n"
        "✅ Поиск по сайтам: OK (12/12)\n"
        "✅ Telegram: OK (3/3) · @itrecruit_ua, @remotejobss, @itfreelancers\n"
        "📊 Найдено: 22 · в базе: 40 · новых: 0\n"
        "\n"
        "✅ Все проверки прошли · 2026-07-15 11:00"
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
    assert "⚠️ Telegram: 2/3 ошибки — @remotejobss" in message
    assert "⚠️ Проверки с ошибками · 2026-07-15 11:00" in message


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
