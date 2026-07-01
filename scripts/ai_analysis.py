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


def main() -> int:
    parser = argparse.ArgumentParser(description="Optional AI analysis for iOS Hunter")
    parser.add_argument("--weekly", action="store_true", help="Append AI summary to weekly report")
    parser.add_argument("--db", default="database/jobs.db", help="SQLite database path")
    args = parser.parse_args()

    analyzer = create_analyzer()
    if not analyzer.enabled():
        print("AI analysis disabled (set OPENAI_API_KEY or GEMINI_API_KEY to enable).")
        return 0

    repo = JobRepository(args.db)
    try:
        if args.weekly:
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
    finally:
        repo.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
