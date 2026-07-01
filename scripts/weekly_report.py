#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.repository import JobRepository
from integrations.public_reports import generate_companies_report, generate_weekly_report


def main() -> int:
    db_path = Path(os.environ.get("JOBS_DB_PATH", "database/jobs.db"))
    repo = JobRepository(db_path, base_dir=ROOT)
    try:
        weekly = generate_weekly_report(repo, ROOT)
        companies = generate_companies_report(repo, ROOT)
        print(f"Weekly report: {weekly}")
        print(f"Companies report: {companies}")
    finally:
        repo.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
