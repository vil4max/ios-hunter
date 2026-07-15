#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import load_settings
from project_sync.manual_card import ManualCard, create_private_card, upsert_private_card


def _ensure_env() -> None:
    defaults = {
        "CAREER_AGENT_TOKEN": os.environ.get("CAREER_AGENT_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
        or "",
        "CAREER_PROJECT_OWNER": os.environ.get("CAREER_PROJECT_OWNER", "vil4max"),
        "CAREER_PROJECT_NUMBER": os.environ.get("CAREER_PROJECT_NUMBER", "3"),
        "GITHUB_REPOSITORY": os.environ.get("GITHUB_REPOSITORY", "vil4max/ios-hunter"),
        "CAREER_AGENT_SYNC_ENABLED": "1",
    }
    token = defaults["CAREER_AGENT_TOKEN"]
    if not token:
        try:
            import subprocess

            token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
            defaults["CAREER_AGENT_TOKEN"] = token
        except Exception:
            pass
    for key, value in defaults.items():
        if value and not os.environ.get(key):
            os.environ[key] = value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upsert a private Career CRM draft card (not a public Issue)."
    )
    parser.add_argument("--company", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--status", default="Applied")
    parser.add_argument("--source", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--applied-at", default=None, help="YYYY-MM-DD")
    parser.add_argument("--follow-up", default=None, help="YYYY-MM-DD")
    parser.add_argument("--priority", default=None, choices=["P0", "P1", "P2"])
    parser.add_argument(
        "--offer-probability",
        default=None,
        choices=["Low", "Medium", "High"],
        help="Your estimate of offer chance",
    )
    parser.add_argument("--notes", default="")
    parser.add_argument(
        "--create-only",
        action="store_true",
        help="Always create a new draft (skip upsert by URL/title)",
    )
    args = parser.parse_args()

    _ensure_env()
    settings = load_settings()
    card = ManualCard(
        company=args.company,
        title=args.title,
        status=args.status,
        source=args.source,
        url=args.url,
        applied_at=args.applied_at,
        follow_up=args.follow_up,
        priority=args.priority,
        offer_probability=args.offer_probability,
        notes=args.notes,
    )
    if args.create_only:
        item_id = create_private_card(settings, card)
        created = True
    else:
        item_id, created = upsert_private_card(settings, card)
    action = "Created" if created else "Updated"
    print(f"{action} private card: {card.company} — {card.title}")
    print(f"Status: {card.status}")
    if card.offer_probability:
        print(f"Offer Probability: {card.offer_probability}")
    print(f"Item: {item_id}")
    print("Board: https://github.com/users/vil4max/projects/3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
