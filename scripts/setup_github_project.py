#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ID = "PVT_kwHOABVlTc4Bdb8R"
STATUS_FIELD_ID = "PVTSSF_lAHOABVlTc4Bdb8RzhX9fr0"
TMP = Path("/tmp/career-agent-gh-graphql.json")


def graphql(query: str, variables: dict | None = None) -> dict:
    payload = {"query": query, "variables": variables or {}}
    TMP.write_text(json.dumps(payload), encoding="utf-8")
    result = subprocess.run(
        ["gh", "api", "graphql", "--input", str(TMP)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    payload_out = json.loads(result.stdout)
    if payload_out.get("errors"):
        raise RuntimeError(json.dumps(payload_out["errors"], indent=2))
    return payload_out["data"]


def existing_field_names() -> set[str]:
    data = graphql(
        """
        query($id: ID!) {
          node(id: $id) {
            ... on ProjectV2 {
              fields(first: 50) {
                nodes {
                  ... on ProjectV2FieldCommon { name }
                }
              }
            }
          }
        }
        """,
        {"id": PROJECT_ID},
    )
    names: set[str] = set()
    for node in ((data.get("node") or {}).get("fields") or {}).get("nodes") or []:
        if isinstance(node, dict) and node.get("name"):
            names.add(str(node["name"]))
    return names


def update_status() -> None:
    options = [
        ("Inbox", "BLUE", "New vacancy"),
        ("Applied", "ORANGE", "Application sent"),
        ("Screening", "PINK", "HR / recruiter screening"),
        ("Technical", "YELLOW", "Technical interview"),
        ("Offer", "GREEN", "Offer received"),
        ("Rejected", "RED", "Rejected or withdrawn"),
        ("Archived", "GRAY", "Not interested / closed"),
    ]
    data = graphql(
        """
        mutation($input: UpdateProjectV2FieldInput!) {
          updateProjectV2Field(input: $input) {
            projectV2Field {
              ... on ProjectV2SingleSelectField {
                name
                options { id name }
              }
            }
          }
        }
        """,
        {
            "input": {
                "fieldId": STATUS_FIELD_ID,
                "singleSelectOptions": [
                    {"name": name, "color": color, "description": desc}
                    for name, color, desc in options
                ],
            }
        },
    )
    field = data["updateProjectV2Field"]["projectV2Field"]
    print("Status options:")
    for opt in field["options"]:
        print(f"  - {opt['name']}")


def create_field(name: str, data_type: str, single_select_options: list[dict] | None = None) -> None:
    variables: dict = {
        "input": {
            "projectId": PROJECT_ID,
            "dataType": data_type,
            "name": name,
        }
    }
    if single_select_options is not None:
        variables["input"]["singleSelectOptions"] = single_select_options
    data = graphql(
        """
        mutation($input: CreateProjectV2FieldInput!) {
          createProjectV2Field(input: $input) {
            projectV2Field {
              ... on ProjectV2Field { id name dataType }
              ... on ProjectV2SingleSelectField {
                id
                name
                options { id name }
              }
            }
          }
        }
        """,
        variables,
    )
    field = data["createProjectV2Field"]["projectV2Field"]
    print(f"Created field: {field.get('name')} ({field.get('dataType', 'SINGLE_SELECT')})")


def main() -> int:
    update_status()
    present = existing_field_names()
    for name in ("URL", "Company", "Source", "Canonical URL"):
        if name in present:
            print(f"Skip existing field: {name}")
            continue
        create_field(name, "TEXT")
    for name in ("Applied At", "Follow Up"):
        if name in present:
            print(f"Skip existing field: {name}")
            continue
        create_field(name, "DATE")
    if "Priority" in present:
        print("Skip existing field: Priority")
    else:
        create_field(
            "Priority",
            "SINGLE_SELECT",
            [
                {"name": "P0", "color": "RED", "description": "Highest"},
                {"name": "P1", "color": "ORANGE", "description": "High"},
                {"name": "P2", "color": "GRAY", "description": "Normal"},
            ],
        )
    if "Offer Probability" in present:
        print("Skip existing field: Offer Probability")
    else:
        create_field(
            "Offer Probability",
            "SINGLE_SELECT",
            [
                {"name": "Low", "color": "RED", "description": "Low chance of offer"},
                {"name": "Medium", "color": "YELLOW", "description": "Medium chance of offer"},
                {"name": "High", "color": "GREEN", "description": "High chance of offer"},
            ],
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
