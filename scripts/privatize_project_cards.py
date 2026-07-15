#!/usr/bin/env python3
from __future__ import annotations

"""
Convert public Project Issues back to private Drafts, then close the Issues.

Safe for Career CRM privacy: Project stays private; repo Issues are closed.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import load_settings
from project_sync.github_client import GitHubClient
from project_sync.manual_card import ManualCard, create_private_card


def _gh_close_issue(repo: str, number: int) -> None:
    subprocess.run(
        ["gh", "issue", "close", str(number), "--repo", repo, "--comment", "Converted to private Project draft (Career CRM)."],
        check=False,
    )


def _snapshot_fields(raw: dict) -> dict[str, str]:
    fields: dict[str, str] = {}
    for node in (raw.get("fieldValues") or {}).get("nodes") or []:
        if not isinstance(node, dict):
            continue
        name = ((node.get("field") or {}).get("name")) or ""
        if not name:
            continue
        if "text" in node and node["text"] is not None:
            fields[name] = str(node["text"])
        elif "date" in node and node["date"] is not None:
            fields[name] = str(node["date"])
        elif "name" in node and node.get("name") is not None and "date" not in node:
            # single select value name
            if name != "Title":
                fields[name] = str(node["name"])
    return fields


def main() -> int:
    os.environ.setdefault("CAREER_PROJECT_OWNER", "vil4max")
    os.environ.setdefault("CAREER_PROJECT_NUMBER", "3")
    os.environ.setdefault("GITHUB_REPOSITORY", "vil4max/ios-hunter")
    os.environ.setdefault("CAREER_AGENT_SYNC_ENABLED", "1")
    if not os.environ.get("CAREER_AGENT_TOKEN"):
        token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
        os.environ["CAREER_AGENT_TOKEN"] = token

    settings = load_settings()
    client = GitHubClient(settings.github_token)
    meta = client.resolve_project(settings.project_owner, settings.project_number)
    items = client.list_project_items(meta.project_id)

    converted = 0
    for raw in items:
        content = raw.get("content") or {}
        # Issue has number; DraftIssue does not
        number = content.get("number")
        if number is None:
            continue
        title = str(content.get("title") or "")
        body = str(content.get("body") or "")
        fields = _snapshot_fields(raw)
        company = fields.get("Company") or (title.split(" — ", 1)[0] if " — " in title else "Unknown")
        role = fields.get("Title") or (title.split(" — ", 1)[1] if " — " in title else title)
        if " — " in title and role == fields.get("Title"):
            role = title.split(" — ", 1)[1]
        status = fields.get("Status") or "Applied"
        card = ManualCard(
            company=company,
            title=role if role != company else title,
            status=status,
            source=fields.get("Source", ""),
            url=fields.get("URL", ""),
            applied_at=fields.get("Applied At"),
            follow_up=fields.get("Follow Up"),
            offer_probability=fields.get("Offer Probability"),
            notes="Re-imported as private draft after public Issue cleanup.\n\n" + body,
        )
        item_id = str(raw.get("id") or "")
        print(f"Converting Issue #{number}: {title} [{status}]")
        client.delete_project_item(meta.project_id, item_id)
        create_private_card(settings, card, client=client)
        _gh_close_issue(settings.github_repository, int(number))
        converted += 1

    print(f"Converted {converted} public Issue card(s) to private drafts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
