from __future__ import annotations

from config.settings import Settings
from project_sync.github_client import ProjectField, ProjectMeta
from project_sync.sync import ProjectSync, build_issue_body, build_issue_title
from tests.conftest import make_vacancy


def _settings(**overrides) -> Settings:
    base = dict(
        github_token="token",
        github_repository="acme/ios-hunter",
        project_owner="acme",
        project_number=1,
        project_board_url="https://github.com/users/acme/projects/1",
        sync_enabled=True,
        seen_gate_enabled=True,
        stale_days=7,
        inbox_new_days=2,
        research_stale_days=5,
    )
    base.update(overrides)
    return Settings(**base)


class FakeClient:
    def __init__(self) -> None:
        self.created_titles: list[str] = []
        self.draft_items: list[str] = []
        self.status_sets: list[str] = []
        self.text_sets: list[tuple[str, str]] = []
        self._by_canonical: dict[str, str] = {}
        self._counter = 10
        self.meta = ProjectMeta(
            project_id="PROJECT",
            status_field=ProjectField(
                id="STATUS",
                name="Status",
                kind="single_select",
                options={"Inbox": "opt-inbox", "Archived": "opt-arch"},
            ),
            fields_by_name={
                "Status": ProjectField(
                    id="STATUS",
                    name="Status",
                    kind="single_select",
                    options={"Inbox": "opt-inbox", "Archived": "opt-arch"},
                ),
                "URL": ProjectField(id="F_URL", name="URL", kind="common"),
                "Company": ProjectField(id="F_CO", name="Company", kind="common"),
                "Source": ProjectField(id="F_SRC", name="Source", kind="common"),
                "Canonical URL": ProjectField(id="F_CAN", name="Canonical URL", kind="common"),
            },
        )

    def resolve_project(self, owner: str, number: int) -> ProjectMeta:
        return self.meta

    def find_project_item_by_canonical_url(self, project_id: str, canonical_url: str) -> str | None:
        return self._by_canonical.get(canonical_url)

    def add_draft_issue(self, project_id: str, *, title: str, body: str = "") -> str:
        self._counter += 1
        item_id = f"DRAFT-{self._counter}"
        self.created_titles.append(title)
        self.draft_items.append(item_id)
        for line in body.splitlines():
            if line.startswith("Canonical-URL: "):
                self._by_canonical[line.removeprefix("Canonical-URL: ")] = item_id
        return item_id

    def set_single_select_field(self, *, project_id: str, item_id: str, field_id: str, option_id: str) -> None:
        self.status_sets.append(option_id)

    def set_text_field(self, *, project_id: str, item_id: str, field_id: str, text: str) -> None:
        self.text_sets.append((field_id, text))
        if field_id == "F_CAN":
            self._by_canonical[text] = item_id


def test_build_issue_includes_canonical_marker() -> None:
    vacancy = make_vacancy(url="https://example.com/jobs/1?utm_source=x")
    body = build_issue_body(vacancy)
    assert "Canonical-URL: https://example.com/jobs/1" in body
    assert build_issue_title(vacancy) == "Acme — Senior iOS Developer"


def test_sync_creates_private_draft_and_sets_inbox() -> None:
    client = FakeClient()
    sync = ProjectSync(_settings(), client=client)  # type: ignore[arg-type]
    result = sync.sync_vacancies([make_vacancy(url="https://example.com/jobs/99")])
    assert result.created_count == 1
    assert result.existing_count == 0
    assert client.draft_items
    assert "opt-inbox" in client.status_sets
    assert any(field_id == "F_CAN" for field_id, _ in client.text_sets)


def test_sync_is_idempotent_for_same_canonical_url() -> None:
    client = FakeClient()
    sync = ProjectSync(_settings(), client=client)  # type: ignore[arg-type]
    vacancy = make_vacancy(url="https://example.com/jobs/42")
    first = sync.sync_vacancies([vacancy])
    second = sync.sync_vacancies([vacancy])
    assert first.created_count == 1
    assert second.existing_count == 1
    assert second.created_count == 0
    assert len(client.draft_items) == 1


def test_sync_skipped_when_disabled() -> None:
    sync = ProjectSync(_settings(sync_enabled=False), client=FakeClient())  # type: ignore[arg-type]
    result = sync.sync_vacancies([make_vacancy()])
    assert result.skipped_disabled is True
    assert result.created_count == 0


def test_seed_archived_uses_archived_status() -> None:
    client = FakeClient()
    sync = ProjectSync(_settings(), client=client)  # type: ignore[arg-type]
    result = sync.seed_archived([make_vacancy(url="https://example.com/legacy/1")])
    assert result.created_count == 1
    assert "opt-arch" in client.status_sets
