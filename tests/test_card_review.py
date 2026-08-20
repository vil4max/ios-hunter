from __future__ import annotations

from datetime import date

from planner.plan import ProjectCard
from project_sync.card_review import append_archive_note, archive_card
from project_sync.github_client import ProjectField, ProjectMeta


def _card() -> ProjectCard:
    return ProjectCard(
        item_id="item",
        issue_number=None,
        title="iOS Developer",
        url="https://example.com/jobs/ios",
        issue_url="",
        company="Acme",
        source="company",
        canonical_url="https://example.com/jobs/ios",
        status="Inbox",
        priority="",
        offer_probability="",
        follow_up=None,
        applied_at=None,
        created_at=None,
        updated_at=None,
        body="Existing notes\n",
    )


class FakeClient:
    def __init__(self) -> None:
        self.status_sets: list[tuple[str, str, str, str]] = []
        self.body = ""
        self.archived: list[tuple[str, str]] = []

    def draft_issue_id_for_item(self, project_id, item_id):
        return "draft"

    def set_single_select_field(self, *, project_id, item_id, field_id, option_id):
        self.status_sets.append((project_id, item_id, field_id, option_id))

    def update_draft_issue(self, draft_id, *, title=None, body=None):
        self.body = body or ""

    def archive_project_item(self, project_id, item_id):
        self.archived.append((project_id, item_id))


def _meta() -> ProjectMeta:
    status = ProjectField("status", "Status", "single_select", {"Archived": "archived"})
    reason = ProjectField(
        "reason",
        "Close Reason",
        "single_select",
        {"Not interested": "not-interested"},
    )
    stage = ProjectField("stage", "Closed Stage", "single_select", {"Inbox": "inbox"})
    return ProjectMeta(
        project_id="project",
        status_field=status,
        fields_by_name={"Status": status, "Close Reason": reason, "Closed Stage": stage},
    )


def test_append_archive_note_is_idempotent() -> None:
    first = append_archive_note(
        "Notes",
        reason="Not interested",
        note="Buenos Aires only",
        archived_at=date(2026, 8, 20),
    )
    second = append_archive_note(
        first,
        reason="Not interested",
        note="Buenos Aires only",
        archived_at=date(2026, 8, 20),
    )
    assert first == second


def test_archive_card_records_reason_stage_and_note() -> None:
    client = FakeClient()

    archive_card(
        client,  # type: ignore[arg-type]
        _meta(),
        _card(),
        reason="Not interested",
        note="Buenos Aires only",
        archived_at=date(2026, 8, 20),
    )

    assert client.status_sets == [
        ("project", "item", "reason", "not-interested"),
        ("project", "item", "stage", "inbox"),
    ]
    assert client.archived == [("project", "item")]
    assert "Buenos Aires only" in client.body
