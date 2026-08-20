from __future__ import annotations

from datetime import date

import pytest

from integrations.vacancy_probe import ProbeResult
from planner.plan import ProjectCard
from project_sync.application_readiness import (
    ApplicationPackage,
    PACKAGE_END,
    PACKAGE_START,
    build_application_package_body,
    prepare_application,
)
from project_sync.github_client import ProjectField, ProjectMeta


def _card() -> ProjectCard:
    return ProjectCard(
        item_id="item",
        issue_number=None,
        title="Senior iOS Engineer",
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
        self.body = ""
        self.status_sets: list[tuple[str, str, str, str]] = []

    def draft_issue_id_for_item(self, project_id, item_id):
        return "draft"

    def update_draft_issue(self, draft_id, *, title=None, body=None):
        self.body = body or ""

    def set_single_select_field(self, *, project_id, item_id, field_id, option_id):
        self.status_sets.append((project_id, item_id, field_id, option_id))


def _meta() -> ProjectMeta:
    status = ProjectField(
        id="status-field",
        name="Status",
        kind="single_select",
        options={"Inbox": "inbox-option"},
    )
    return ProjectMeta(project_id="project", status_field=status, fields_by_name={"Status": status})


def test_build_application_package_replaces_previous_package() -> None:
    first = build_application_package_body(
        "Notes",
        ApplicationPackage(resume="Senior iOS CV"),
        prepared_at=date(2026, 8, 20),
    )
    second = build_application_package_body(
        first,
        ApplicationPackage(resume="Lead iOS CV", message="Hello"),
        prepared_at=date(2026, 8, 21),
    )

    assert second.count(PACKAGE_START) == 1
    assert second.count(PACKAGE_END) == 1
    assert "Lead iOS CV" in second
    assert "Senior iOS CV" not in second


def test_prepare_application_verifies_open_role_without_changing_status() -> None:
    client = FakeClient()
    probe = lambda url, card_title="": ProbeResult(url, False, False, 200, "open")

    prepare_application(
        client,  # type: ignore[arg-type]
        _meta(),
        _card(),
        ApplicationPackage(resume="Senior iOS CV", answers=("Ukraine",)),
        probe=probe,
        prepared_at=date(2026, 8, 20),
    )

    assert "Submission: owner approval required" in client.body
    assert client.status_sets == []


def test_prepare_application_does_not_mutate_closed_role() -> None:
    client = FakeClient()
    probe = lambda url, card_title="": ProbeResult(url, True, False, 200, "closed")

    with pytest.raises(RuntimeError, match="vacancy is closed"):
        prepare_application(
            client,  # type: ignore[arg-type]
            _meta(),
            _card(),
            ApplicationPackage(resume="Senior iOS CV"),
            probe=probe,
        )

    assert client.body == ""
    assert client.status_sets == []
