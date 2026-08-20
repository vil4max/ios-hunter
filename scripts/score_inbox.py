#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.fit_score import assess_fit, load_candidate_profile
from collector.companies import collect_all
from config.settings import load_settings
from parser.deduplicate import deduplicate
from parser.normalize import Vacancy, canonicalize_url, normalize_many
from planner.plan import ProjectCard, load_cards_from_github
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


def _body_field(body: str, name: str) -> str | None:
    match = re.search(rf"(?im)^\*\*{re.escape(name)}:\*\*\s*(.+)$", body or "")
    return match.group(1).strip() if match else None


def _fallback_vacancy(card: ProjectCard) -> Vacancy:
    return Vacancy(
        company=card.company,
        title=card.title,
        url=card.url or card.canonical_url,
        source=card.source or "company",
        location=_body_field(card.body, "Location"),
        remote=_body_field(card.body, "Remote"),
    )


def main() -> int:
    default_career_root = ROOT.parent / "Profile" / "career"
    parser = argparse.ArgumentParser(
        description="Score current Career CRM Inbox vacancies for first-pass review.",
    )
    parser.add_argument(
        "--resume",
        type=Path,
        default=default_career_root / "presentation" / "resume.md",
    )
    parser.add_argument(
        "--career",
        type=Path,
        default=default_career_root / "career.md",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    _ensure_env()
    settings = load_settings()
    client = GitHubClient(settings.github_token)
    cards = [
        card
        for card in load_cards_from_github(client, settings)
        if card.status == "Inbox"
    ]
    collection = collect_all()
    vacancies, _duplicates_removed = deduplicate(
        normalize_many(
            [job for source in collection.source_results for job in source.jobs]
        )
    )
    vacancies_by_url = {vacancy.canonical_url: vacancy for vacancy in vacancies}
    profile = load_candidate_profile(args.resume, args.career)
    rows = []
    for card in cards:
        key = canonicalize_url(card.url or card.canonical_url)
        vacancy = vacancies_by_url.get(key) or _fallback_vacancy(card)
        assessment = assess_fit(vacancy, profile)
        rows.append(
            {
                "score": assessment.score,
                "recommendation": assessment.recommendation,
                "confidence": assessment.confidence,
                "company": vacancy.company,
                "title": vacancy.title,
                "location": vacancy.location or "unknown",
                "remote": vacancy.remote or "unknown",
                "english_requirement": assessment.english_requirement,
                "url": vacancy.url,
                "reasons": list(assessment.reasons),
                "blockers": list(assessment.blockers),
            }
        )
    rows.sort(key=lambda row: (-int(row["score"]), str(row["company"]), str(row["title"])))
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    for index, row in enumerate(rows, start=1):
        blockers = "; ".join(row["blockers"]) or "none"
        print(
            f"{index:02d}. {row['score']:>3}% {row['recommendation']:<6} "
            f"[{row['confidence']}] {row['company']} — {row['title']} | "
            f"{row['location']} / {row['remote']} | "
            f"English: {row['english_requirement']} | blockers: {blockers}"
        )
        print(f"    {row['url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
