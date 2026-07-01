#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.engine import create_analyzer
from database.repository import JobRepository


def run_weekly_summary(db_path: Path) -> bool:
    analyzer = create_analyzer()
    if not analyzer.enabled():
        print("AI analysis disabled (set OPENAI_API_KEY or GEMINI_API_KEY to enable).")
        return False

    repo = JobRepository(db_path, base_dir=ROOT)
    try:
        rows = repo.history_change_counts(days=7)
        context = "\n".join(f"{row['change_type']}: {row['count']}" for row in rows)
        result = analyzer.summarize_week(context)
        report_dir = ROOT / "reports/weekly"
        report_dir.mkdir(parents=True, exist_ok=True)
        latest = report_dir / "latest.md"
        existing = latest.read_text(encoding="utf-8") if latest.exists() else ""
        summary_block = f"\n\n## AI Summary\n\n{result.summary}\n"
        latest.write_text(existing + summary_block, encoding="utf-8")
        print("Weekly AI summary appended.")
        return True
    finally:
        repo.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Optional AI analysis for iOS Hunter")
    parser.add_argument("--weekly", action="store_true", help="Append AI summary to weekly report")
    parser.add_argument("--db", default="database/jobs.db", help="SQLite database path")
    args = parser.parse_args()

    if not args.weekly:
        print("Nothing to do. Pass --weekly to append an AI summary.")
        return 2

    return 0 if run_weekly_summary(ROOT / args.db) else 1


if __name__ == "__main__":
    raise SystemExit(main())
