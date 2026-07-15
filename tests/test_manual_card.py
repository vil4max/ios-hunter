from __future__ import annotations

from config.settings import Settings
from project_sync.github_client import ProjectField, ProjectMeta
from project_sync.manual_card import ManualCard, build_draft_body, upsert_private_card


def _settings() -> Settings:
    return Settings(
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


class FakeClient:
    def __init__(self) -> None:
        self.created_titles: list[str] = []
        self.updated_drafts: list[tuple[str, str | None, str | None]] = []
        self.status_sets: list[str] = []
        self._items: dict[str, dict] = {}
        self._by_canonical: dict[str, str] = {}
        self._by_title: dict[str, str] = {}
        self._counter = 10
        self.meta = ProjectMeta(
            project_id="PROJECT",
            status_field=ProjectField(
                id="STATUS",
                name="Status",
                kind="single_select",
                options={
                    "Applied": "opt-applied",
                    "Screening": "opt-screening",
                },
            ),
            fields_by_name={
                "Status": ProjectField(
                    id="STATUS",
                    name="Status",
                    kind="single_select",
                    options={
                        "Applied": "opt-applied",
                        "Screening": "opt-screening",
                    },
                ),
                "URL": ProjectField(id="F_URL", name="URL", kind="common"),
                "Company": ProjectField(id="F_CO", name="Company", kind="common"),
                "Source": ProjectField(id="F_SRC", name="Source", kind="common"),
                "Canonical URL": ProjectField(id="F_CAN", name="Canonical URL", kind="common"),
                "Applied At": ProjectField(id="F_APP", name="Applied At", kind="date"),
                "Follow Up": ProjectField(id="F_FU", name="Follow Up", kind="date"),
                "Offer Probability": ProjectField(
                    id="F_OP",
                    name="Offer Probability",
                    kind="single_select",
                    options={"Low": "opt-low", "Medium": "opt-med", "High": "opt-high"},
                ),
            },
        )

    def resolve_project(self, owner: str, number: int) -> ProjectMeta:
        return self.meta

    def find_project_item_by_canonical_url(self, project_id: str, canonical_url: str) -> str | None:
        return self._by_canonical.get(canonical_url)

    def find_project_item_by_title(self, project_id: str, title: str) -> str | None:
        return self._by_title.get(title)

    def find_project_item_by_company(self, project_id: str, company: str) -> str | None:
        needle = company.strip().casefold()
        hits = [
            item_id
            for item_id, meta in self._items.items()
            if meta["title"].split(" — ", 1)[0].strip().casefold() == needle
        ]
        return hits[0] if len(hits) == 1 else None

    def draft_issue_id_for_item(self, project_id: str, item_id: str) -> str | None:
        item = self._items.get(item_id)
        if not item:
            return None
        return str(item["draft_id"])

    def update_draft_issue(
        self,
        draft_issue_id: str,
        *,
        title: str | None = None,
        body: str | None = None,
    ) -> None:
        self.updated_drafts.append((draft_issue_id, title, body))

    def add_draft_issue(self, project_id: str, *, title: str, body: str = "") -> str:
        self._counter += 1
        item_id = f"ITEM-{self._counter}"
        draft_id = f"DRAFT-{self._counter}"
        self.created_titles.append(title)
        self._items[item_id] = {"draft_id": draft_id, "title": title, "body": body}
        self._by_title[title] = item_id
        for line in body.splitlines():
            if line.startswith("Canonical-URL: "):
                self._by_canonical[line.removeprefix("Canonical-URL: ")] = item_id
        return item_id

    def set_single_select_field(self, *, project_id: str, item_id: str, field_id: str, option_id: str) -> None:
        self.status_sets.append(option_id)

    def set_text_field(self, *, project_id: str, item_id: str, field_id: str, text: str) -> None:
        if field_id == "F_CAN":
            self._by_canonical[text] = item_id

    def set_date_field(self, *, project_id: str, item_id: str, field_id: str, date_value: str) -> None:
        return None


def test_build_draft_body_includes_marker_and_notes() -> None:
    card = ManualCard(
        company="Acme",
        title="Senior iOS",
        status="Applied",
        url="https://example.com/jobs/1?utm=x",
        notes="screening booked",
    )
    body = build_draft_body(card)
    assert "<!-- career-agent-manual -->" in body
    assert "Canonical-URL: https://example.com/jobs/1" in body
    assert "screening booked" in body


def test_upsert_creates_then_updates_same_url() -> None:
    client = FakeClient()
    card = ManualCard(
        company="Credit Booster",
        title="Senior Mobile Developer",
        status="Applied",
        url="https://example.com/cb",
        offer_probability="Medium",
    )
    first_id, created = upsert_private_card(_settings(), card, client=client)  # type: ignore[arg-type]
    assert created is True
    assert first_id.startswith("ITEM-")
    assert "opt-applied" in client.status_sets

    card.status = "Screening"
    card.follow_up = "2026-07-16"
    card.notes = "Meet 14:00"
    second_id, created_again = upsert_private_card(_settings(), card, client=client)  # type: ignore[arg-type]
    assert created_again is False
    assert second_id == first_id
    assert len(client.created_titles) == 1
    assert client.updated_drafts
    assert "opt-screening" in client.status_sets


def test_upsert_matches_same_company_when_title_differs() -> None:
    client = FakeClient()
    first = ManualCard(
        company="Visual Craft",
        title="Senior iOS Engineer",
        status="Screening",
    )
    item_id, created = upsert_private_card(_settings(), first, client=client)  # type: ignore[arg-type]
    assert created is True

    second = ManualCard(
        company="Visual Craft",
        title="Senior iOS (Swift) Engineer",
        status="Applied",
        url="https://djinni.co/jobs/836367-senior-ios-swift-engineer/",
    )
    same_id, created_again = upsert_private_card(_settings(), second, client=client)  # type: ignore[arg-type]
    assert created_again is False
    assert same_id == item_id
    assert len(client.created_titles) == 1
