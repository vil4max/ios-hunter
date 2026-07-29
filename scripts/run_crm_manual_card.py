#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import ACTIVE_PIPELINE_STATUSES, load_settings
from planner.plan import parse_project_item
from project_sync.github_client import GitHubClient
from project_sync.manual_card import (
    ManualCard,
    find_existing_item_id,
    seed_seen_from_manual_card,
    upsert_private_card,
)

ONCE_PATH = ROOT / "database" / "crm_upsert_once.json"


def _from_workflow_inputs() -> dict[str, str]:
    mapping = {
        "company": "INPUT_COMPANY",
        "title": "INPUT_TITLE",
        "url": "INPUT_URL",
        "status": "INPUT_STATUS",
        "channel": "INPUT_CHANNEL",
        "source": "INPUT_SOURCE",
        "applied_at": "INPUT_APPLIED_AT",
        "salary": "INPUT_SALARY",
        "summary": "INPUT_SUMMARY",
        "recruiter": "INPUT_RECRUITER",
        "close_reason": "INPUT_CLOSE_REASON",
        "closed_stage": "INPUT_CLOSED_STAGE",
    }
    return {key: (os.environ.get(env) or "").strip() for key, env in mapping.items()}


def _from_once_file() -> dict[str, str] | None:
    if not ONCE_PATH.is_file():
        return None
    data = json.loads(ONCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Expected object in {ONCE_PATH}")
    if not data:
        return None
    return {str(k): str(v).strip() if v is not None else "" for k, v in data.items()}


def _current_status(settings, card: ManualCard) -> str | None:
    if not settings.project_owner or settings.project_number <= 0:
        return None
    client = GitHubClient(settings.github_token)
    meta = client.resolve_project(settings.project_owner, settings.project_number)
    item_id = find_existing_item_id(client, meta.project_id, card)
    if not item_id:
        return None
    for raw in client.list_project_items(meta.project_id):
        if str(raw.get("id") or "") != item_id:
            continue
        parsed = parse_project_item(raw)
        return parsed.status if parsed else None
    return None


def main() -> int:
    os.environ.setdefault("CAREER_AGENT_SYNC_ENABLED", "1")
    event = os.environ.get("EVENT_NAME") or ""
    if event == "workflow_dispatch":
        raw = _from_workflow_inputs()
    else:
        loaded = _from_once_file()
        if loaded is None:
            print(f"No pending upsert in {ONCE_PATH}; nothing to do.")
            return 0
        raw = loaded

    company = raw.get("company") or ""
    title = raw.get("title") or ""
    if not company or not title:
        raise SystemExit("company and title are required")

    status = raw.get("status") or "Applied"
    closed_stage = raw.get("closed_stage") or None
    close_reason = raw.get("close_reason") or None

    card = ManualCard(
        company=company,
        title=title,
        status=status,
        source=raw.get("source") or "",
        channel=raw.get("channel") or None,
        recruiter=raw.get("recruiter") or None,
        summary=raw.get("summary") or None,
        salary=raw.get("salary") or None,
        url=raw.get("url") or "",
        applied_at=raw.get("applied_at") or None,
        close_reason=close_reason,
        closed_stage=closed_stage,
    )
    settings = load_settings()

    if status == "Archived" and not closed_stage:
        current = _current_status(settings, card)
        if current and current in ACTIVE_PIPELINE_STATUSES:
            card.closed_stage = current
            print(f"Closed Stage inferred from board: {current}")
        elif current and current not in {"Archived", "History"}:
            card.closed_stage = current
            print(f"Closed Stage inferred from board: {current}")

    item_id, created = upsert_private_card(settings, card)
    action = "Created" if created else "Updated"
    print(f"{action} private card: {card.company} — {card.title}")
    print(f"Status: {card.status}")
    if card.close_reason:
        print(f"Close Reason: {card.close_reason}")
    if card.closed_stage:
        print(f"Closed Stage: {card.closed_stage}")
    print(f"Item: {item_id}")
    print("Board: https://github.com/users/vil4max/projects/3")
    seeded, seen_key_value = seed_seen_from_manual_card(card)
    if seeded:
        print(f"Seen seeded: {seen_key_value}")
    elif seen_key_value:
        print(f"Seen already present: {seen_key_value}")
    else:
        print("Seen skipped: no URL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
