from __future__ import annotations

import pytest

from project_sync.github_client import GitHubClient, GitHubGraphQLError, ProjectItemIndex
from project_sync.sync import ProjectSync
from tests.conftest import make_vacancy
from tests.test_project_sync import FakeClient, _settings


def _page(items, *, next_page=False, cursor=None):
    return {"node": {"items": {
        "nodes": items,
        "pageInfo": {"hasNextPage": next_page, "endCursor": cursor},
    }}}


def test_sync_loads_every_page_once_including_archived_and_indexes_new_drafts(monkeypatch):
    client = FakeClient()
    transport = GitHubClient("fake")
    calls = []
    pages = [
        _page([{"id": "unrelated", "content": {"title": "Other — iOS Developer"}}], next_page=True, cursor="second"),
        _page([{"id": "archived", "isArchived": True, "content": {
            "title": "Sigma — Senior iOS Engineer (#42)",
            "body": "Canonical-URL: https://example.com/legacy?utm_source=email\n",
        }}]),
    ]

    def graphql(query, variables):
        calls.append(variables)
        return pages.pop(0)

    monkeypatch.setattr(transport, "graphql", graphql)
    monkeypatch.setattr(client, "list_project_items", transport.list_project_items)
    sync = ProjectSync(_settings(), client=client)
    new_roles = [make_vacancy(company=f"Company {i}", url=f"https://example.com/new/{i}") for i in range(10)]
    result = sync.sync_vacancies([
        make_vacancy(company="Sigma Software", title="Senior iOS Engineer", url="https://example.com/new-city"),
        *new_roles,
        make_vacancy(company="Different title", url="https://example.com/new/0?utm_source=email"),
        make_vacancy(company="Company 1", url="https://example.com/new-city-1"),
    ])
    assert result.created_count == 10
    assert result.existing_count == 3
    assert result.existing[0].item_id == "archived"
    assert len(calls) == 2
    assert [call["after"] for call in calls] == [None, "second"]
    assert all(call["archivedStates"] == ["ARCHIVED", "NOT_ARCHIVED"] for call in calls)
    assert len(client.draft_items) == 10


def test_index_normalizes_fields_and_body_markers_without_matching_url_prefixes():
    index = ProjectItemIndex.from_items([
        {"id": "body", "content": {"body": "Canonical-URL: https://example.com/job/10?utm_source=x"}},
        {"id": "fields", "fieldValues": {"nodes": [
            {"field": {"name": "Canonical URL"}, "text": "https://example.com/job/20?utm_source=x"},
            {"field": {"name": "URL"}, "text": "https://example.com/alternative?utm_source=x"},
        ]}},
    ])
    assert index.find("https://example.com/job/10", "", "") == "body"
    assert index.find("https://example.com/job/1", "", "") is None
    assert index.find("https://example.com/job/20", "", "") == "fields"
    assert index.find("https://example.com/alternative", "", "") == "fields"


@pytest.mark.parametrize("bad_page", [
    {"node": None},
    {"node": {"items": {"nodes": []}}},
    {"node": {"items": {"nodes": [], "pageInfo": {"hasNextPage": None}}}},
    _page([None]),
    _page([{}]),
    _page([], next_page=True),
    _page([], next_page=True, cursor="second"),
])
def test_partial_or_broken_pagination_fails_entire_sync_without_writes(monkeypatch, bad_page):
    client = FakeClient()
    transport = GitHubClient("fake")
    pages = [_page([{"id": "existing"}], next_page=True, cursor="second"), bad_page]
    calls = []

    def graphql(query, variables):
        calls.append(variables)
        return pages.pop(0)

    monkeypatch.setattr(transport, "graphql", graphql)
    monkeypatch.setattr(client, "list_project_items", transport.list_project_items)
    result = ProjectSync(_settings(), client=client).sync_vacancies([
        make_vacancy(), make_vacancy(company="Other", url="https://example.com/other"),
    ])
    assert result.failed_count == 2
    assert result.created_count == result.existing_count == 0
    assert client.draft_items == []
    assert len(calls) == 2


def test_graphql_error_during_pagination_does_not_cache_partial_snapshot(monkeypatch):
    client = FakeClient()
    transport = GitHubClient("fake")
    calls = []

    def graphql(query, variables):
        calls.append(variables)
        if len(calls) == 1:
            return _page([{"id": "existing"}], next_page=True, cursor="second")
        raise GitHubGraphQLError("access denied")

    monkeypatch.setattr(transport, "graphql", graphql)
    monkeypatch.setattr(client, "list_project_items", transport.list_project_items)
    sync = ProjectSync(_settings(), client=client)
    result = sync.sync_vacancies([make_vacancy(), make_vacancy(company="Other")])
    assert result.failed_count == 2
    assert all(item.error == "access denied" for item in result.failed)
    assert sync._index is None
    assert client.draft_items == []
    assert len(calls) == 2


def test_field_failure_does_not_duplicate_successfully_created_draft(monkeypatch):
    client = FakeClient()

    def set_status(**kwargs):
        raise GitHubGraphQLError("field update failed")

    monkeypatch.setattr(client, "set_single_select_field", set_status)
    result = ProjectSync(_settings(), client=client).sync_vacancies([
        make_vacancy(), make_vacancy(url="https://example.com/other-city"),
    ])
    assert result.failed_count == 1
    assert result.existing_count == 1
    assert len(client.draft_items) == 1
    assert client.list_calls == 1


def test_snapshot_is_owned_by_sync_instance_not_shared_client():
    client = FakeClient()
    first = ProjectSync(_settings(), client=client)
    assert first.sync_vacancies([make_vacancy()]).created_count == 1
    client.items.append({"id": "manual", "content": {
        "title": "Other — Senior iOS Developer", "body": "Canonical-URL: https://example.com/manual",
    }})
    second = ProjectSync(_settings(), client=client)
    result = second.sync_vacancies([make_vacancy(company="Other", url="https://example.com/manual")])
    assert result.existing[0].item_id == "manual"
    assert client.list_calls == 2
