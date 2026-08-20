#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import CLOSE_REASON_OPTIONS, load_settings
from parser.normalize import canonicalize_url
from planner.plan import load_cards_from_github
from project_sync.card_review import archive_card
from project_sync.github_client import GitHubClient


def _ensure_env() -> None:
    defaults = {
        "CAREER_PROJECT_OWNER": "vil4max",
        "CAREER_PROJECT_NUMBER": "3",
        "GITHUB_REPOSITORY": "vil4max/ios-hunter",
        "CAREER_AGENT_SYNC_ENABLED": "1",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)
    if not os.environ.get("CAREER_AGENT_TOKEN"):
        os.environ["CAREER_AGENT_TOKEN"] = subprocess.check_output(
            ["gh", "auth", "token"],
            text=True,
        ).strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archive one private Career CRM vacancy by URL.",
    )
    parser.add_argument("url", help="Vacancy URL already present on Career CRM")
    parser.add_argument(
        "--reason",
        default="Not interested",
        choices=CLOSE_REASON_OPTIONS,
    )
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    _ensure_env()
    settings = load_settings()
    client = GitHubClient(settings.github_token)
    meta = client.resolve_project(settings.project_owner, settings.project_number)
    canonical = canonicalize_url(args.url)
    cards = load_cards_from_github(client, settings)
    card = next(
        (
            candidate
            for candidate in cards
            if canonicalize_url(candidate.url or candidate.canonical_url) == canonical
        ),
        None,
    )
    if card is None:
        raise RuntimeError("vacancy card not found on Career CRM")
    if card.status in {"Archived", "History"}:
        print(f"Already archived: {card.display_title}")
        return 0
    archive_card(
        client,
        meta,
        card,
        reason=args.reason,
        note=args.note,
    )
    print(f"Archived: {card.display_title}")
    print(f"Reason: {args.reason}; previous stage: {card.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
