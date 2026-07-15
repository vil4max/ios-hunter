#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import load_settings
from planner.plan import build_plan, load_cards_from_github
from project_sync.github_client import GitHubClient


def main() -> int:
    settings = load_settings()
    if not settings.configured_for_sync:
        print(
            "Daily report requires Sync config "
            "(CAREER_AGENT_SYNC_ENABLED, CAREER_AGENT_TOKEN, project owner/number, GITHUB_REPOSITORY).",
            file=sys.stderr,
        )
        return 1

    client = GitHubClient(settings.github_token)
    cards = load_cards_from_github(client, settings)
    plan = build_plan(cards, settings)
    print(
        "Daily CRM report is Project-only (no Telegram).\n"
        f"Board: {settings.project_board_url or '(unset)'}\n"
        f"Cards: {len(cards)}\n"
        f"Inbox: {plan.status_counts.get('Inbox', 0)}\n"
        f"Today tasks: {len(plan.today_tasks)}\n"
        f"New: {len(plan.new_vacancies)}\n"
        f"Attention: {len(plan.needs_attention)}\n"
        f"Follow-ups due: {len(plan.pending_follow_ups)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
