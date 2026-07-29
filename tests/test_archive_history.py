from __future__ import annotations

from datetime import date, datetime, timezone

from planner.plan import ProjectCard
from project_sync.archive_history import find_stale_archived_cards, migrate_archived_to_history
from project_sync.github_client import ProjectField, ProjectMeta


def _card(**overrides) -> ProjectCard:
    values = {
        "item_id": "item-1",
        "issue_number": None,
        "title": "iOS Developer",
        "url": "https://example.com/job/1",
        "issue_url": "",
        "company": "Acme",
        "source": "company",
        "canonical_url": "https://example.com/job/1",
        "status": "Archived",
        "priority": "",
        "offer_probability": "",
        "follow_up": None,
        "applied_at": date(2026, 1, 1),
        "created_at": None,
        "updated_at": datetime(2026, 7, 20, tzinfo=timezone.utc),
        "body": "",
    }
    values.update(overrides)
    return ProjectCard(**values)


class _FakeClient:
    def __init__(self) -> None:
        self.status_sets: list[tuple[str, str, str, str]] = []

    def resolve_project(self, owner: str, number: int) -> ProjectMeta:
        return ProjectMeta(
            project_id="P1",
            status_field=ProjectField(
                id="F_STATUS",
                name="Status",
                kind="single_select",
                options={"History": "opt-history"},
            ),
            fields_by_name={},
        )

    def set_single_select_field(
        self,
        *,
        project_id: str,
        item_id: str,
        field_id: str,
        option_id: str,
    ) -> None:
        self.status_sets.append((project_id, item_id, field_id, option_id))


def test_find_stale_archived_cards_sorts_by_title() -> None:
    today = date(2026, 7, 29)
    cards = [
        _card(item_id="b", company="Zeta", title="Role B"),
        _card(item_id="a", company="Alpha", title="Role A"),
        _card(
            item_id="fresh",
            company="Fresh",
            title="Role",
            applied_at=date(2026, 6, 1),
        ),
    ]
    stale = find_stale_archived_cards(cards, today=today, min_days=100)
    assert [card.item_id for card in stale] == ["a", "b"]


def test_migrate_archived_to_history_updates_status() -> None:
    from config.settings import Settings

    settings = Settings(
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
    client = _FakeClient()
    stale = _card(item_id="old")
    migrated = migrate_archived_to_history(
        settings,
        client=client,
        cards=[stale],
        today=date(2026, 7, 29),
        apply=True,
        meta=client.resolve_project("a", 1),
    )
    assert migrated == [stale]
    assert client.status_sets == [("P1", "old", "F_STATUS", "opt-history")]


def test_migrate_archived_to_history_dry_run_skips_updates() -> None:
    from config.settings import Settings

    settings = Settings(
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
    client = _FakeClient()
    migrated = migrate_archived_to_history(
        settings,
        client=client,
        cards=[_card(item_id="old")],
        today=date(2026, 7, 29),
        apply=False,
    )
    assert len(migrated) == 1
    assert client.status_sets == []
