from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crm.applications import list_applications, log_application, update_stage
from crm.followups import render_followup_digest, send_followup_reminders
from crm.stats import render_crm_stats
from database.repository import JobRepository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="iOS Hunter Recruiter CRM")
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_parser = subparsers.add_parser("apply", help="Log a job application")
    apply_parser.add_argument("--company", required=True)
    apply_parser.add_argument("--title", required=True)
    apply_parser.add_argument("--source", default="company")
    apply_parser.add_argument("--job-id")
    apply_parser.add_argument("--resume", dest="resume_version")
    apply_parser.add_argument("--follow-up-days", type=int, default=7)

    subparsers.add_parser("list", help="List recent applications")
    subparsers.add_parser("followups", help="Show due follow-ups")
    subparsers.add_parser("remind", help="Send follow-up digest to Telegram")
    subparsers.add_parser("stats", help="Show CRM stats")

    stage_parser = subparsers.add_parser("stage", help="Update application stage")
    stage_parser.add_argument("--id", type=int, required=True)
    stage_parser.add_argument(
        "--stage",
        required=True,
        choices=["applied", "hr_screen", "technical", "offer", "rejected", "ghosted"],
    )
    stage_parser.add_argument("--reason")

    args = parser.parse_args(argv)
    db_path = Path(os.environ.get("JOBS_DB_PATH", "database/jobs.db"))
    repo = JobRepository(db_path)

    try:
        if args.command == "apply":
            app_id = log_application(
                repo,
                company=args.company,
                title=args.title,
                source=args.source,
                job_id=args.job_id,
                resume_version=args.resume_version,
                follow_up_days=args.follow_up_days,
            )
            print(f"Logged application #{app_id}")
        elif args.command == "list":
            for app in list_applications(repo):
                print(
                    f"#{app.id} [{app.stage}] {app.company} — {app.title} "
                    f"({app.source}, {app.applied_at})"
                )
        elif args.command == "followups":
            print(render_followup_digest(repo) or "No follow-ups due.")
        elif args.command == "remind":
            count = send_followup_reminders(repo)
            print(f"Sent reminders for {count} application(s).")
        elif args.command == "stats":
            print(render_crm_stats(repo))
        elif args.command == "stage":
            update_stage(repo, args.id, args.stage, args.reason)
            print(f"Updated application #{args.id} → {args.stage}")
    finally:
        repo.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
