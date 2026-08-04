#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collector.companies import collect_all
from config.schedule import KYIV
from config.settings import load_settings
from database.daily_email_days import default_daily_email_days_path, email_sent_for_day
from database.seen import default_seen_path, load_seen
from database.source_health import classify_degraded, default_baseline_path, load_baseline
from integrations.email_smtp import credentials_configured, report_email_to, send_email
from planner.plan import build_plan, load_cards_from_github
from project_sync.github_client import GitHubClient
from reporter.daily import build_collect_day_summary, format_full_daily_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Send Career Agent daily email report.")
    parser.add_argument(
        "--send-claimed",
        action="store_true",
        help="Send after the day was claimed+committed (skip local claim check).",
    )
    args = parser.parse_args()

    settings = load_settings()
    if not settings.configured_for_sync:
        print(
            "Daily report requires Sync config "
            "(CAREER_AGENT_SYNC_ENABLED, CAREER_AGENT_TOKEN, project owner/number, GITHUB_REPOSITORY).",
            file=sys.stderr,
        )
        return 1
    if not credentials_configured():
        print(
            "Daily email requires SMTP_USER + SMTP_PASS "
            f"(REPORT_EMAIL_TO defaults to {report_email_to()}).",
            file=sys.stderr,
        )
        return 1

    now = datetime.now(KYIV)
    day = now.strftime("%Y-%m-%d")
    email_days_path = default_daily_email_days_path(ROOT)
    if not args.send_claimed and email_sent_for_day(email_days_path, day):
        print(f"Daily email already sent for {day} — skip")
        return 0
    if args.send_claimed and not email_sent_for_day(email_days_path, day):
        print(
            f"Daily email day {day} is not claimed — refuse send-claimed",
            file=sys.stderr,
        )
        return 1

    client = GitHubClient(settings.github_token)
    cards = load_cards_from_github(client, settings)
    plan = build_plan(cards, settings)

    seen = load_seen(default_seen_path(ROOT))
    collect_result = collect_all()
    results = collect_result.source_results
    baseline = load_baseline(default_baseline_path(ROOT))
    classify_degraded(results, baseline)
    summary = build_collect_day_summary(seen, results, now=now)

    body = format_full_daily_report(
        plan,
        summary,
        board_url=settings.project_board_url,
        now=now,
    )
    subject = f"Career Agent · {day}"
    send_email(subject=subject, body=body)
    print(f"Daily email sent to {report_email_to()}")
    print(
        f"Cards: {len(cards)} · new today: {summary.new_today_count} · "
        f"sources failed: {summary.sources_failed} · degraded: {summary.sources_degraded}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
