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
from project_sync.manual_card import ManualCard, create_private_card


# Migrated from Profile/career/job-search + GlobalLogic apply (2026-07-14).
# Private drafts only — no public Issues. No recruiter/salary/feedback text.
HISTORY: list[ManualCard] = [
    ManualCard(
        company="Visual Craft",
        title="Senior iOS Engineer",
        status="Screening",
        source="Djinni",
        applied_at="2026-07-10",
        follow_up="2026-07-20",
        offer_probability="Medium",
        notes="Migrated from career/job-search. Recruiter screening in progress.",
    ),
    ManualCard(
        company="Intellias",
        title="Senior iOS Engineer",
        status="Applied",
        source="Company Career Page",
        url="https://career.intellias.com/vacancy/senior-ios-engineer-30434",
        applied_at="2026-07-10",
        follow_up="2026-07-17",
        offer_probability="Medium",
        notes="Migrated from career/job-search.",
    ),
    ManualCard(
        company="ZONE3000",
        title="Middle+ / Senior iOS Developer",
        status="Applied",
        source="Company Career Page",
        applied_at="2026-07-10",
        follow_up="2026-07-17",
        offer_probability="Low",
        notes="Migrated from career/job-search.",
    ),
    ManualCard(
        company="PersonalInvest",
        title="Senior iOS Engineer (AI-first B2C)",
        status="Applied",
        source="LinkedIn Feed",
        applied_at="2026-07-06",
        follow_up="2026-07-13",
        offer_probability="Medium",
        notes="Migrated from career/job-search. LinkedIn outreach.",
    ),
    ManualCard(
        company="KSA Fintech",
        title="Senior iOS Developer",
        status="Applied",
        source="LinkedIn Feed",
        applied_at="2026-07-13",
        follow_up="2026-07-20",
        offer_probability="Low",
        notes="Migrated from career/job-search. Employer confidential (LinkedIn outreach).",
    ),
    ManualCard(
        company="Grid Dynamics",
        title="Senior iOS Engineer",
        status="Rejected",
        source="Recruiter Outreach",
        applied_at="2026-04-25",
        offer_probability="Low",
        notes="Migrated from career/interview/pipeline. Outcome: rejected after technical (T2 vs T3). Detail stays in private interview diary.",
    ),
    ManualCard(
        company="NIX",
        title="Middle iOS Developer",
        status="Rejected",
        source="Unknown",
        offer_probability="Low",
        notes="Migrated from career/interview/pipeline. CV screening reject. Wrong seniority lane.",
    ),
    ManualCard(
        company="GlobalLogic",
        title="iOS Software Engineer",
        status="Applied",
        source="GlobalLogic careers",
        url="https://www.globallogic.com/ua/careers/ios-software-engineer-irc300022/",
        applied_at="2026-07-14",
        follow_up="2026-07-21",
        offer_probability="Medium",
        notes="Applied 2026-07-14 (Telegram Collect discovery).",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Import career history as private Project drafts.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    if not settings.github_token:
        settings_env = {
            "CAREER_AGENT_TOKEN": os.environ.get("CAREER_AGENT_TOKEN") or os.environ.get("GITHUB_TOKEN"),
            "CAREER_PROJECT_OWNER": os.environ.get("CAREER_PROJECT_OWNER", "vil4max"),
            "CAREER_PROJECT_NUMBER": os.environ.get("CAREER_PROJECT_NUMBER", "3"),
            "GITHUB_REPOSITORY": os.environ.get("GITHUB_REPOSITORY", "vil4max/ios-hunter"),
            "CAREER_AGENT_SYNC_ENABLED": "1",
        }
        for key, value in settings_env.items():
            if value and not os.environ.get(key):
                os.environ[key] = value
        settings = load_settings()

    if args.dry_run:
        for card in HISTORY:
            print(f"[dry-run] {card.status:12} {card.company} — {card.title}")
        print(f"Total: {len(HISTORY)}")
        return 0

    if not settings.github_token or not settings.project_owner or settings.project_number <= 0:
        print("Missing token or project config.", file=sys.stderr)
        return 1

    created = 0
    for card in HISTORY:
        item_id = create_private_card(settings, card)
        created += 1
        print(f"OK {card.status:12} {card.company} — {card.title} ({item_id})")

    print(f"Created {created} private draft cards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
