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
from project_sync.hirify_sync import run_hirify_sync
from reporter.hirify_sync import notify_hirify_sync


def _ensure_env() -> None:
    defaults = {
        "CAREER_AGENT_TOKEN": os.environ.get("CAREER_AGENT_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
        or "",
        "CAREER_PROJECT_OWNER": os.environ.get("CAREER_PROJECT_OWNER", "vil4max"),
        "CAREER_PROJECT_NUMBER": os.environ.get("CAREER_PROJECT_NUMBER", "3"),
        "GITHUB_REPOSITORY": os.environ.get("GITHUB_REPOSITORY", "vil4max/ios-hunter"),
        "CAREER_AGENT_SYNC_ENABLED": os.environ.get("CAREER_AGENT_SYNC_ENABLED", "1"),
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
        description="Sync Hirify Applications Excel export into Career CRM."
    )
    parser.add_argument(
        "--xlsx",
        default=None,
        help="Path to my_applications_*.xlsx (default: latest in ~/Downloads)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and plan without writing Project cards or hirify_seen.",
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        help="Skip Telegram notification even when mutations exist.",
    )
    args = parser.parse_args()

    _ensure_env()
    settings = load_settings()
    if not settings.configured_for_sync:
        print(
            "Hirify sync requires Sync config "
            "(CAREER_AGENT_SYNC_ENABLED, CAREER_AGENT_TOKEN, project owner/number, GITHUB_REPOSITORY).",
            file=sys.stderr,
        )
        return 1

    try:
        result = run_hirify_sync(
            settings,
            xlsx_path=args.xlsx,
            dry_run=args.dry_run,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    notified = False
    if not args.no_telegram:
        notified = notify_hirify_sync(result)

    mutations = result.mutations or []
    created = sum(1 for m in mutations if m.action in {"created", "would_create"})
    updated = sum(1 for m in mutations if m.action in {"updated", "would_update", "noted", "would_note"})
    noop = sum(1 for m in mutations if m.action == "noop")
    print(
        f"Xlsx={result.xlsx_path or '-'} rows={result.rows} "
        f"skipped_seen={result.skipped_seen} created={created} "
        f"updated={updated} noop={noop} notified={notified} dry_run={args.dry_run}"
    )
    for mutation in mutations:
        if mutation.action == "noop":
            continue
        company = mutation.row.company or "?"
        title = mutation.row.job_title or "?"
        print(
            f"- {mutation.action}: {company} — {title} "
            f"{mutation.previous_status}->{mutation.new_status}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
