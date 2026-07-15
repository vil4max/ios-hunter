from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from integrations.notify import CollectReportStats
from planner.plan import DailyPlan, ProjectCard
from reporter.daily import format_daily_dashboard
from reporter.hourly import format_hourly_inbox_alert

_KYIV = ZoneInfo("Europe/Kyiv")


def test_hourly_alert_has_no_vacancy_list() -> None:
    now = datetime(2026, 7, 15, 11, 0, tzinfo=_KYIV)
    stats = CollectReportStats(
        found=10,
        seen_total=8,
        new_count=2,
        duplicates_removed=1,
        failed_source_names=(),
    )
    message = format_hourly_inbox_alert(
        created_count=2,
        board_url="https://github.com/users/acme/projects/1",
        stats=stats,
        now=now,
    )
    assert message.startswith("Inbox +2 · 2026-07-15 11:00")
    assert "Новых карточек: 2" in message
    assert "https://example.com" not in message
    assert "Senior iOS" not in message


def test_daily_dashboard_sections() -> None:
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
    assert "New vacancies" in message
    assert "Needs attention" in message
    assert "Today's tasks" in message
    assert "Pipeline statistics" in message
    assert "Daily summary" in message
    assert "Acme — iOS Engineer" in message
