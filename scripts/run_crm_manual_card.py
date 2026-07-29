#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import load_settings
from project_sync.manual_card import ManualCard, seed_seen_from_manual_card, upsert_private_card


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


def main() -> int:
    os.environ.setdefault("CAREER_AGENT_SYNC_ENABLED", "1")
    if os.environ.get("EVENT_NAME") != "workflow_dispatch":
        raise SystemExit("Expected workflow_dispatch event")
    raw = _from_workflow_inputs()

    company = raw.get("company") or ""
    title = raw.get("title") or ""
    if not company or not title:
        raise SystemExit("company and title are required")

    card = ManualCard(
        company=company,
        title=title,
        status=raw.get("status") or "Applied",
        source=raw.get("source") or "",
        channel=raw.get("channel") or None,
        recruiter=raw.get("recruiter") or None,
        summary=raw.get("summary") or None,
        salary=raw.get("salary") or None,
        url=raw.get("url") or "",
        applied_at=raw.get("applied_at") or None,
        close_reason=raw.get("close_reason") or None,
        closed_stage=raw.get("closed_stage") or None,
    )
    settings = load_settings()
    item_id, created = upsert_private_card(settings, card)
    action = "Created" if created else "Updated"
    print(f"{action} private card: {card.company} — {card.title}")
    print(f"Status: {card.status}")
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
