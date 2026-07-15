from __future__ import annotations

from datetime import date, datetime, timezone

from config.settings import Settings
from planner.plan import ProjectCard, _split_company_title, build_plan, parse_project_item


def _settings() -> Settings:
    return Settings(
        github_token="t",
        github_repository="a/b",
        project_owner="a",
        project_number=1,
        project_board_url="",
        sync_enabled=True,
        seen_gate_enabled=True,
        stale_days=7,
        inbox_new_days=2,
        research_stale_days=5,
    )


def _card(**overrides) -> ProjectCard:
    base = dict(
        item_id="1",
        issue_number=1,
        title="Senior iOS",
        url="https://example.com/1",
        issue_url="",
        company="Acme",
        source="test",
        canonical_url="https://example.com/1",
        status="Inbox",
        priority="P1",
        offer_probability="",
        follow_up=None,
        applied_at=None,
        created_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return ProjectCard(**base)


def test_split_company_title_avoids_double_company() -> None:
    company, title = _split_company_title(
        "PersonalInvest — Senior iOS Engineer (AI-first B2C)",
        "PersonalInvest",
    )
    assert company == "PersonalInvest"
    assert title == "Senior iOS Engineer (AI-first B2C)"
    card = _card(company=company, title=title)
    assert card.display_title == "PersonalInvest — Senior iOS Engineer (AI-first B2C)"


def test_parse_project_item_strips_duplicated_company() -> None:
    raw = {
        "id": "ITEM1",
        "updatedAt": "2026-07-15T00:00:00Z",
        "fieldValues": {
            "nodes": [
                {"text": "PersonalInvest", "field": {"name": "Company"}},
                {"name": "Applied", "field": {"name": "Status"}},
            ]
        },
        "content": {
            "title": "PersonalInvest — Senior iOS Engineer (AI-first B2C)",
            "body": "",
        },
    }
    card = parse_project_item(raw)
    assert card is not None
    assert card.display_title == "PersonalInvest — Senior iOS Engineer (AI-first B2C)"


def test_planner_prioritizes_follow_ups_and_stale() -> None:
    today = date(2026, 7, 15)
    cards = [
        _card(item_id="inbox", status="Inbox", title="New role"),
        _card(
            item_id="stale",
            status="Applied",
            title="Stale apply",
            updated_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        ),
        _card(
            item_id="follow",
            status="Screening",
            title="Call back",
            follow_up=date(2026, 7, 15),
        ),
        _card(
            item_id="applied",
            status="Applied",
            title="Waiting reply",
            follow_up=date(2026, 7, 22),
        ),
        _card(
            item_id="screen-soon",
            status="Screening",
            title="Screen next week",
            follow_up=date(2026, 7, 20),
        ),
        _card(item_id="arch", status="Archived", title="Old"),
    ]
    plan = build_plan(cards, _settings(), today=today)
    assert plan.today_tasks[0].item_id == "follow"
    assert any(c.item_id == "stale" for c in plan.needs_attention)
    assert any(c.item_id == "inbox" for c in plan.new_vacancies)
    assert plan.status_counts.get("Archived") == 1
    assert all(c.item_id != "arch" for c in plan.today_tasks)
    assert all(c.item_id != "applied" for c in plan.today_tasks)
    assert [c.item_id for c in plan.upcoming_interviews] == ["screen-soon"]
    assert "applied" not in [c.item_id for c in plan.upcoming_interviews]
