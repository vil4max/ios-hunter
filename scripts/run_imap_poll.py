#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import load_settings
from integrations.email_imap import credentials_configured
from project_sync.mail_sync import run_mail_sync
from reporter.imap_poll import notify_imap_poll


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Poll Gmail IMAP for recruiter mail and sync GitHub Project cards."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify and match without writing Project cards or email_seen.",
    )
    parser.add_argument("--limit", type=int, default=40, help="Max recent messages to fetch")
    parser.add_argument("--since-days", type=int, default=7, help="IMAP SINCE window in days")
    args = parser.parse_args()

    settings = load_settings()
    if not settings.configured_for_sync:
        print(
            "IMAP poll requires Sync config "
            "(CAREER_AGENT_SYNC_ENABLED, CAREER_AGENT_TOKEN, project owner/number, GITHUB_REPOSITORY).",
            file=sys.stderr,
        )
        return 1
    if not credentials_configured():
        print(
            "IMAP poll requires SMTP_USER + SMTP_PASS (Gmail App Password).",
            file=sys.stderr,
        )
        return 1

    result = run_mail_sync(
        settings,
        dry_run=args.dry_run,
        limit=args.limit,
        since_days=args.since_days,
    )
    notified = notify_imap_poll(result, board_url=settings.project_board_url)
    mutations = result.mutations or []
    updates = sum(1 for m in mutations if m.action in {"updated", "would_update"})
    unmatched = sum(1 for m in mutations if m.unmatched)
    print(
        f"Fetched={result.fetched} skipped_seen={result.skipped_seen} "
        f"ignored={result.ignored} updates={updates} unmatched={unmatched} "
        f"notified={notified} dry_run={args.dry_run}"
    )
    for mutation in mutations:
        if mutation.action in {"ignored", "noop"}:
            continue
        company = mutation.event.company or mutation.event.from_addr
        print(
            f"- {mutation.action}: {company} [{mutation.event.kind}] "
            f"{mutation.previous_status}->{mutation.new_status}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
