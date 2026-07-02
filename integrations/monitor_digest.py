from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from collector.types import SourceResult
from database.repository import JobRepository
from integrations.telegram import send_message
from parser.activity import ActivitySummary


def render_monitor_digest(
    activity: ActivitySummary,
    open_roles: int,
    tracked_total: int,
    source_results: list[SourceResult],
) -> str:
    total_sources = len(source_results)
    failed_sources = sum(1 for result in source_results if result.status == "failed")
    healthy_sources = total_sources - failed_sources

    if failed_sources == 0:
        sources_line = f"Sources: {total_sources}/{total_sources} OK"
    else:
        sources_line = (
            f"Sources: {healthy_sources}/{total_sources} OK ({failed_sources} failed)"
        )

    checked_at = datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%d %b %Y, %H:%M")

    return f"""✅ iOS Hunter

Run Activity
Actionable: {activity.actionable}
New: {activity.new}
Updated: {activity.updated}
Reopened: {activity.reopened}
Closed: {activity.closed}

{activity.headline()}

Open roles now: {open_roles}
Tracking in total: {tracked_total}
{sources_line}

Checked {checked_at} Kyiv"""


def send_monitor_digest(
    repo: JobRepository,
    activity: ActivitySummary,
    source_results: list[SourceResult],
    profile: dict,
) -> bool:
    if not profile.get("telegram", {}).get("enabled", True):
        return False

    message = render_monitor_digest(
        activity,
        repo.count_open_jobs(),
        repo.count_tracked_jobs(),
        source_results,
    )
    send_message(message)
    return True
