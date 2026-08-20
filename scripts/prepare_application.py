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

from config.settings import load_settings
from parser.normalize import canonicalize_url
from planner.plan import load_cards_from_github
from project_sync.application_readiness import ApplicationPackage, prepare_application
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
        description="Verify a vacancy and save its application package on the Inbox card.",
    )
    parser.add_argument("--url", required=True, help="Vacancy URL already present on the board")
    parser.add_argument("--cv", required=True, help="CV version label, not a local file path")
    parser.add_argument("--message", default="", help="Prepared application message")
    parser.add_argument("--answer", action="append", default=[], help="Screening answer")
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
    prepare_application(
        client,
        meta,
        card,
        ApplicationPackage(
            resume=args.cv.strip(),
            message=args.message.strip(),
            answers=tuple(answer.strip() for answer in args.answer if answer.strip()),
        ),
    )
    print(f"Application package prepared: {card.display_title}")
    print("Submission remains blocked until owner approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
