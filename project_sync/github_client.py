from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests


GRAPHQL_URL = "https://api.github.com/graphql"


class GitHubGraphQLError(RuntimeError):
    pass


@dataclass
class ProjectField:
    id: str
    name: str
    kind: str
    options: dict[str, str] = field(default_factory=dict)


@dataclass
class ProjectMeta:
    project_id: str
    status_field: ProjectField | None
    fields_by_name: dict[str, ProjectField]


@dataclass
class IssueRef:
    id: str
    number: int
    url: str
    title: str
    body: str = ""


class GitHubClient:
    def __init__(self, token: str, *, timeout: int = 45) -> None:
        self._token = token
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "ios-hunter-career-agent/1.0",
            }
        )

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._session.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables or {}},
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            messages = "; ".join(str(err.get("message", err)) for err in payload["errors"])
            raise GitHubGraphQLError(messages)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise GitHubGraphQLError("GraphQL response missing data")
        return data

    def resolve_repository_id(self, owner: str, name: str) -> str:
        data = self.graphql(
            """
            query($owner: String!, $name: String!) {
              repository(owner: $owner, name: $name) { id }
            }
            """,
            {"owner": owner, "name": name},
        )
        repo = data.get("repository") or {}
        repo_id = repo.get("id")
        if not repo_id:
            raise GitHubGraphQLError(f"Repository not found: {owner}/{name}")
        return str(repo_id)

    def resolve_project(self, owner: str, number: int) -> ProjectMeta:
        user_data = self.graphql(
            """
            query($login: String!, $number: Int!) {
              user(login: $login) {
                projectV2(number: $number) {
                  id
                  fields(first: 50) {
                    nodes {
                      __typename
                      ... on ProjectV2FieldCommon { id name }
                      ... on ProjectV2SingleSelectField {
                        id
                        name
                        options { id name }
                      }
                    }
                  }
                }
              }
            }
            """,
            {"login": owner, "number": number},
        )
        project = ((user_data.get("user") or {}).get("projectV2")) or None
        if not project:
            try:
                org_data = self.graphql(
                    """
                    query($login: String!, $number: Int!) {
                      organization(login: $login) {
                        projectV2(number: $number) {
                          id
                          fields(first: 50) {
                            nodes {
                              __typename
                              ... on ProjectV2FieldCommon { id name }
                              ... on ProjectV2SingleSelectField {
                                id
                                name
                                options { id name }
                              }
                            }
                          }
                        }
                      }
                    }
                    """,
                    {"login": owner, "number": number},
                )
                project = ((org_data.get("organization") or {}).get("projectV2")) or None
            except GitHubGraphQLError:
                project = None
        if not project or not project.get("id"):
            raise GitHubGraphQLError(f"Project not found: {owner}#{number}")

        fields_by_name: dict[str, ProjectField] = {}
        status_field: ProjectField | None = None
        for node in (project.get("fields") or {}).get("nodes") or []:
            if not isinstance(node, dict) or not node.get("id") or not node.get("name"):
                continue
            options: dict[str, str] = {}
            for opt in node.get("options") or []:
                if isinstance(opt, dict) and opt.get("id") and opt.get("name"):
                    options[str(opt["name"])] = str(opt["id"])
            kind = "single_select" if options else "common"
            parsed = ProjectField(
                id=str(node["id"]),
                name=str(node["name"]),
                kind=kind,
                options=options,
            )
            fields_by_name[parsed.name] = parsed
            if parsed.name == "Status":
                status_field = parsed

        return ProjectMeta(
            project_id=str(project["id"]),
            status_field=status_field,
            fields_by_name=fields_by_name,
        )

    def find_issue_by_canonical_url(self, owner: str, repo: str, canonical_url: str) -> IssueRef | None:
        needle = f'Canonical-URL: {canonical_url} in:body repo:{owner}/{repo}'
        data = self.graphql(
            """
            query($q: String!) {
              search(query: $q, type: ISSUE, first: 5) {
                nodes {
                  ... on Issue {
                    id
                    number
                    url
                    title
                    body
                    state
                  }
                }
              }
            }
            """,
            {"q": needle},
        )
        nodes = ((data.get("search") or {}).get("nodes")) or []
        marker = f"Canonical-URL: {canonical_url}"
        for node in nodes:
            if not isinstance(node, dict) or not node.get("id"):
                continue
            body = str(node.get("body") or "")
            if marker not in body:
                continue
            return IssueRef(
                id=str(node["id"]),
                number=int(node["number"]),
                url=str(node.get("url") or ""),
                title=str(node.get("title") or ""),
                body=body,
            )
        return None

    def create_issue(
        self,
        repository_id: str,
        *,
        title: str,
        body: str,
        label_ids: list[str] | None = None,
    ) -> IssueRef:
        issue_input: dict[str, Any] = {
            "repositoryId": repository_id,
            "title": title,
            "body": body,
        }
        if label_ids:
            issue_input["labelIds"] = label_ids
        data = self.graphql(
            """
            mutation($input: CreateIssueInput!) {
              createIssue(input: $input) {
                issue { id number url title body }
              }
            }
            """,
            {"input": issue_input},
        )
        issue = ((data.get("createIssue") or {}).get("issue")) or {}
        if not issue.get("id"):
            raise GitHubGraphQLError("createIssue returned no issue")
        return IssueRef(
            id=str(issue["id"]),
            number=int(issue["number"]),
            url=str(issue.get("url") or ""),
            title=str(issue.get("title") or title),
            body=str(issue.get("body") or body),
        )

    def resolve_label_id(self, owner: str, repo: str, name: str) -> str | None:
        data = self.graphql(
            """
            query($owner: String!, $name: String!, $label: String!) {
              repository(owner: $owner, name: $name) {
                label(name: $label) { id }
              }
            }
            """,
            {"owner": owner, "name": repo, "label": name},
        )
        label = ((data.get("repository") or {}).get("label")) or {}
        label_id = label.get("id")
        return str(label_id) if label_id else None

    def add_project_item(self, project_id: str, content_id: str) -> str:
        data = self.graphql(
            """
            mutation($projectId: ID!, $contentId: ID!) {
              addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
                item { id }
              }
            }
            """,
            {"projectId": project_id, "contentId": content_id},
        )
        item = ((data.get("addProjectV2ItemById") or {}).get("item")) or {}
        item_id = item.get("id")
        if not item_id:
            raise GitHubGraphQLError("addProjectV2ItemById returned no item")
        return str(item_id)

    def add_draft_issue(self, project_id: str, *, title: str, body: str = "") -> str:
        data = self.graphql(
            """
            mutation($input: AddProjectV2DraftIssueInput!) {
              addProjectV2DraftIssue(input: $input) {
                projectItem { id }
              }
            }
            """,
            {
                "input": {
                    "projectId": project_id,
                    "title": title,
                    "body": body,
                }
            },
        )
        item = ((data.get("addProjectV2DraftIssue") or {}).get("projectItem")) or {}
        item_id = item.get("id")
        if not item_id:
            raise GitHubGraphQLError("addProjectV2DraftIssue returned no item")
        return str(item_id)

    def set_date_field(
        self,
        *,
        project_id: str,
        item_id: str,
        field_id: str,
        date_value: str,
    ) -> None:
        self.graphql(
            """
            mutation($input: UpdateProjectV2ItemFieldValueInput!) {
              updateProjectV2ItemFieldValue(input: $input) {
                projectV2Item { id }
              }
            }
            """,
            {
                "input": {
                    "projectId": project_id,
                    "itemId": item_id,
                    "fieldId": field_id,
                    "value": {"date": date_value},
                }
            },
        )

    def set_single_select_field(
        self,
        *,
        project_id: str,
        item_id: str,
        field_id: str,
        option_id: str,
    ) -> None:
        self.graphql(
            """
            mutation($input: UpdateProjectV2ItemFieldValueInput!) {
              updateProjectV2ItemFieldValue(input: $input) {
                projectV2Item { id }
              }
            }
            """,
            {
                "input": {
                    "projectId": project_id,
                    "itemId": item_id,
                    "fieldId": field_id,
                    "value": {"singleSelectOptionId": option_id},
                }
            },
        )

    def set_text_field(
        self,
        *,
        project_id: str,
        item_id: str,
        field_id: str,
        text: str,
    ) -> None:
        self.graphql(
            """
            mutation($input: UpdateProjectV2ItemFieldValueInput!) {
              updateProjectV2ItemFieldValue(input: $input) {
                projectV2Item { id }
              }
            }
            """,
            {
                "input": {
                    "projectId": project_id,
                    "itemId": item_id,
                    "fieldId": field_id,
                    "value": {"text": text},
                }
            },
        )

    def list_project_items(self, project_id: str, *, page_size: int = 50) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            data = self.graphql(
                """
                query($id: ID!, $first: Int!, $after: String) {
                  node(id: $id) {
                    ... on ProjectV2 {
                      items(first: $first, after: $after) {
                        pageInfo { hasNextPage endCursor }
                        nodes {
                          id
                          updatedAt
                          fieldValues(first: 30) {
                            nodes {
                              ... on ProjectV2ItemFieldTextValue {
                                text
                                field { ... on ProjectV2FieldCommon { name } }
                              }
                              ... on ProjectV2ItemFieldDateValue {
                                date
                                field { ... on ProjectV2FieldCommon { name } }
                              }
                              ... on ProjectV2ItemFieldSingleSelectValue {
                                name
                                field { ... on ProjectV2FieldCommon { name } }
                              }
                            }
                          }
                          content {
                            ... on Issue {
                              id
                              number
                              title
                              url
                              body
                              createdAt
                              updatedAt
                              state
                            }
                            ... on DraftIssue {
                              title
                              body
                            }
                          }
                        }
                      }
                    }
                  }
                }
                """,
                {"id": project_id, "first": page_size, "after": cursor},
            )
            node = data.get("node") or {}
            connection = node.get("items") or {}
            for item in connection.get("nodes") or []:
                if isinstance(item, dict):
                    items.append(item)
            page_info = connection.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
            if not cursor:
                break
        return items
