from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from integrations.notify import CollectReportStats
from integrations.telegram import TELEGRAM_MAX_LENGTH
from planner.plan import (
    DailyPlan,
    ProjectCard,
    archived_canonical_urls,
    archived_role_keys,
    exclude_archived_vacancies,
)
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
        "📬 +2 новые вакансии\n"
        "\n"
        "1. Acme — Senior iOS Engineer\n"
        "   https://example.com/a\n"
        "2. Beta — Swift Developer\n"
        "   https://example.com/b\n"
        "\n"
        "🟢 Система в порядке · 2026-07-15 11:00"
    )
    assert "🔗" not in message
    assert "github.com" not in message
    assert "Следующая проверка" not in message


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
        "📬 +1 новая вакансия\n"
        "\n"
        "1. SmartTek Solutions — Senior iOS Engineer\n"
        "   https://t.me/itrecruit_ua/123\n"
        "\n"
        "🟢 Система в порядке · 2026-07-15 11:00"
    )
    assert "🔗" not in message
    assert "https://board" not in message
    assert "📝" not in message
    assert "📅" not in message
    assert "📡" not in message
    assert "Следующая проверка" not in message


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
        live=[make_vacancy(company="EPAM", url="https://example.com/epam/1")],
    )
    assert message == (
        "📭 Новых вакансий нет\n"
        "\n"
        "🟢 Система в порядке · 2026-07-15 11:00"
    )
    assert "Живые" not in message
    assert "Сбор OK" not in message
    assert "📊" not in message
    assert "Следующая проверка" not in message


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
        degraded_source_names=("Binary Studio",),
    )
    message = format_hourly_heartbeat(stats=stats, now=now)
    assert message == (
        "📭 Новых вакансий нет\n"
        "\n"
        "⚠️ Поиск по сайтам: SoftServe\n"
        "⚠️ Telegram: remotejobss\n"
        "🕐 2026-07-15 11:00"
    )
    assert "Следующая проверка" not in message
    assert "@remotejobss" not in message
    assert "Binary Studio" not in message
    assert "🔕" not in message
    assert "Система в порядке" not in message


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
    assert messages[0].startswith("📬 +24 новые вакансии (1/")
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


def test_notify_heartbeat_has_no_live_block(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr("reporter.hourly.send_message", sent.append)
    now = datetime(2026, 7, 27, 23, 0, tzinfo=_KYIV)
    stats = CollectReportStats(found=3, seen_total=3, new_count=0, duplicates_removed=0)
    sync = SyncResult(skipped_disabled=True)
    assert notify_hourly_inbox(
        sync,
        [],
        stats=stats,
        now=now,
        live=[make_vacancy(company="Paybis", url="https://example.com/paybis")],
    )
    assert sent == [
        "📭 Новых вакансий нет\n"
        "\n"
        "🟢 Система в порядке · 2026-07-27 23:00"
    ]
    assert "Следующая проверка" not in sent[0]


def test_exclude_archived_vacancies_by_url_and_role_key() -> None:
    cards = [
        ProjectCard(
            item_id="1",
            issue_number=None,
            title="Middle Software Engineer (IOS Native)",
            url="https://jobs.dou.ua/companies/sombra/vacancies/366864/",
            issue_url="",
            company="Sombra",
            source="dou",
            canonical_url="https://jobs.dou.ua/companies/sombra/vacancies/366864",
            status="Archived",
            priority="",
            offer_probability="",
            follow_up=None,
            applied_at=None,
            created_at=None,
            updated_at=None,
        ),
        ProjectCard(
            item_id="2",
            issue_number=None,
            title="Keep",
            url="https://example.com/keep",
            issue_url="",
            company="Paybis",
            source="",
            canonical_url="https://example.com/keep",
            status="Applied",
            priority="",
            offer_probability="",
            follow_up=None,
            applied_at=None,
            created_at=None,
            updated_at=None,
        ),
    ]
    vacancies = [
        make_vacancy(
            company="Sombra",
            title="Middle Software Engineer (IOS Native)",
            url="https://sombrainc.com/careers/middle-software-engineer-ios-native",
        ),
        make_vacancy(company="Paybis", title="Lead iOS Developer", url="https://example.com/paybis"),
        make_vacancy(
            company="Sombra",
            title="Middle Software Engineer (IOS Native)",
            url="https://jobs.dou.ua/companies/sombra/vacancies/366864/?x=1",
        ),
    ]
    urls = archived_canonical_urls(cards)
    roles = archived_role_keys(cards)
    active = exclude_archived_vacancies(vacancies, archived_urls=urls, archived_roles=roles)
    assert [item.company for item in active] == ["Paybis"]


def test_archived_canonical_urls_collects_archived_only() -> None:
    cards = [
        ProjectCard(
            item_id="1",
            issue_number=None,
            title="Keep",
            url="https://example.com/keep",
            issue_url="",
            company="Paybis",
            source="",
            canonical_url="https://example.com/keep",
            status="Applied",
            priority="",
            offer_probability="",
            follow_up=None,
            applied_at=None,
            created_at=None,
            updated_at=None,
        ),
        ProjectCard(
            item_id="2",
            issue_number=None,
            title="Drop",
            url="https://example.com/drop/",
            issue_url="",
            company="MWDN",
            source="",
            canonical_url="",
            status="Archived",
            priority="",
            offer_probability="",
            follow_up=None,
            applied_at=None,
            created_at=None,
            updated_at=None,
        ),
    ]
    assert archived_canonical_urls(cards) == {"https://example.com/drop"}


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
        status_counts={"Inbox": 1, "Applied": 0, "Archived": 2},
        cards=[
            card,
            ProjectCard(
                item_id="old",
                issue_number=1,
                title="Legacy",
                url="",
                issue_url="",
                company="OldCo",
                source="",
                canonical_url="",
                status="Archived",
                priority="",
                offer_probability="",
                follow_up=None,
                applied_at=None,
                created_at=datetime(2024, 3, 1, tzinfo=_KYIV),
                updated_at=None,
            ),
            ProjectCard(
                item_id="new-arch",
                issue_number=2,
                title="Recent",
                url="",
                issue_url="",
                company="NewCo",
                source="",
                canonical_url="",
                status="Archived",
                priority="",
                offer_probability="",
                follow_up=None,
                applied_at=None,
                created_at=datetime(2026, 6, 20, tzinfo=_KYIV),
                updated_at=None,
            ),
        ],
    )
    now = datetime(2026, 7, 15, 7, 0, tzinfo=_KYIV)
    message = format_daily_dashboard(plan, board_url="https://board", now=now)
    assert "Career Agent · 2026-07-15" in message
    assert "Acme — iOS Engineer" in message
    assert "Archived (recent): 1" in message
    assert "Archived (100d+ stale): 1" in message


def test_full_daily_report_is_human_summary() -> None:
    from collector.types import SourceResult
    from reporter.daily import build_collect_day_summary, format_full_daily_report

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
    focus = ProjectCard(
        item_id="2",
        issue_number=4,
        title="Senior iOS",
        url="https://example.com/old",
        issue_url="https://github.com/a/b/issues/4",
        company="Beta",
        source="test",
        canonical_url="https://example.com/old",
        status="Applied",
        priority="P1",
        offer_probability="Medium",
        follow_up=None,
        applied_at=None,
        created_at=None,
        updated_at=None,
    )
    plan = DailyPlan(
        today_tasks=[focus, card],
        new_vacancies=[card],
        needs_attention=[],
        pending_follow_ups=[focus],
        upcoming_interviews=[],
        status_counts={"Inbox": 1, "Applied": 1, "Archived": 1},
        cards=[
            card,
            focus,
            ProjectCard(
                item_id="arch",
                issue_number=9,
                title="Old Archived",
                url="",
                issue_url="",
                company="Zeta",
                source="",
                canonical_url="",
                status="Archived",
                priority="",
                offer_probability="",
                follow_up=None,
                applied_at=None,
                created_at=datetime(2023, 1, 1, tzinfo=_KYIV),
                updated_at=None,
            ),
        ],
    )
    now = datetime(2026, 7, 15, 18, 0, tzinfo=_KYIV)
    seen = {
        "https://example.com/new": {
            "title": "Senior iOS",
            "company": "Beta",
            "first_seen": "2026-07-15T10:00:00+00:00",
        },
        "https://example.com/old": {
            "title": "Old Role",
            "company": "Gamma",
            "first_seen": "2026-07-14T10:00:00+00:00",
        },
    }
    sources = [
        SourceResult(
            source_id="a",
            source_name="Acme",
            source_url=None,
            jobs=[{"title": "x"}],
            status="healthy",
            error=None,
            response_ms=1,
            items_scanned=1,
        ),
        SourceResult(
            source_id="b",
            source_name="Broken",
            source_url=None,
            jobs=[],
            status="failed",
            error="boom",
            response_ms=1,
            items_scanned=0,
        ),
    ]
    summary = build_collect_day_summary(seen, sources, now=now)
    message = format_full_daily_report(plan, summary, board_url="https://board", now=now)
    assert "📬 Career Agent · 15.07.2026" in message
    assert "🔍 Сбор за день" in message
    assert "Fail: Broken" in message
    assert "🆕 Новых сегодня: 1" in message
    assert "📝 Beta — Senior iOS · Applied" in message
    assert "ещё Inbox" not in message
    assert "https://example.com/new" not in message
    assert message.count("https://") == 1
    assert message.strip().endswith("🔗 https://board")
    assert "📝 Beta — Senior iOS · Applied" in message
    assert "offer:Medium" not in message


def test_new_today_shows_inbox_vs_moved() -> None:
    from reporter.daily import CollectDaySummary, format_full_daily_report

    inbox = ProjectCard(
        item_id="1",
        issue_number=1,
        title="Senior iOS Developer",
        url="https://jobs.dou.ua/companies/breeze/vacancies/365262/",
        issue_url="",
        company="Breeze",
        source="dou",
        canonical_url="https://jobs.dou.ua/companies/breeze/vacancies/365262",
        status="Inbox",
        priority="",
        offer_probability="",
        follow_up=None,
        applied_at=None,
        created_at=None,
        updated_at=None,
    )
    applied = ProjectCard(
        item_id="2",
        issue_number=2,
        title="Senior iOS Engineer",
        url="https://ua.indeed.com/viewjob?jk=abc",
        issue_url="",
        company="Robots & Pencils",
        source="indeed",
        canonical_url="https://ua.indeed.com/viewjob?jk=abc",
        status="Applied",
        priority="",
        offer_probability="",
        follow_up=None,
        applied_at=None,
        created_at=None,
        updated_at=None,
    )
    plan = DailyPlan(
        today_tasks=[applied],
        new_vacancies=[inbox],
        needs_attention=[],
        pending_follow_ups=[],
        upcoming_interviews=[],
        status_counts={"Inbox": 1, "Applied": 1},
        cards=[inbox, applied],
    )
    summary = CollectDaySummary(
        new_today_count=3,
        new_today=(
            ("Breeze", "Senior iOS Developer", "https://jobs.dou.ua/companies/breeze/vacancies/365262"),
            ("Robots & Pencils", "Senior iOS Engineer", "https://ua.indeed.com/viewjob?jk=abc"),
            ("Ghost Co", "iOS Dev", "https://example.com/ghost"),
        ),
        seen_total=10,
        sources_total=10,
        sources_healthy=10,
        jobs_found=5,
    )
    now = datetime(2026, 7, 29, 18, 0, tzinfo=_KYIV)
    message = format_full_daily_report(plan, summary, board_url="https://board", now=now)
    assert "🆕 Новых сегодня: 3" in message
    assert "📥 Breeze — Senior iOS Developer · Inbox" in message
    assert "📝 Robots & Pencils — Senior iOS Engineer · Applied" in message
    assert "⚠️ Ghost Co — iOS Dev · нет карточки" in message
    assert "📥 Inbox 1 · 📝 Applied 1" in message or "📥 Inbox 1" in message
