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
from parser.normalize import canonicalize_url
from planner.plan import parse_project_item
from project_sync.github_client import GitHubClient

ONCE_PATH = ROOT / "database" / "crm_lookup_once.json"


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
    _ensure_env()
    if not ONCE_PATH.is_file():
        print(f"No lookup request in {ONCE_PATH}")
        return 0
    raw = json.loads(ONCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        print("Empty lookup request; nothing to do.")
        return 0

    needles = [
        canonicalize_url(str(raw.get("url") or "")),
        str(raw.get("company") or "").strip().casefold(),
        str(raw.get("title") or "").strip().casefold(),
        str(raw.get("query") or "").strip().casefold(),
    ]
    needles = [n for n in needles if n]

    settings = load_settings()
    client = GitHubClient(settings.github_token)
    meta = client.resolve_project(settings.project_owner, settings.project_number)
    matches: list[dict[str, str]] = []
    for item in client.list_project_items(meta.project_id):
        card = parse_project_item(item)
        if not card:
            continue
        blob = " ".join(
            [
                card.title or "",
                card.company or "",
                card.url or "",
                card.canonical_url or "",
                card.status or "",
                card.source or "",
            ]
        ).casefold()
        urls = {
            canonicalize_url(card.url or ""),
            canonicalize_url(card.canonical_url or ""),
        }
        hit = False
        for needle in needles:
            if needle.startswith("http") and needle in urls:
                hit = True
                break
            if needle and needle in blob:
                hit = True
                break
        if hit:
            matches.append(
                {
                    "item_id": card.item_id,
                    "title": card.title,
                    "company": card.company,
                    "status": card.status,
                    "url": card.url or card.canonical_url,
                    "source": card.source or "",
                }
            )

    print(f"Lookup needles: {needles}")
    print(f"Matches: {len(matches)}")
    for row in matches:
        print(
            f"- [{row['status']}] {row['company']} — {row['title']} | "
            f"{row['url']} | {row['item_id']}"
        )
    if not matches:
        print("No matching Project cards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
