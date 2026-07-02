from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from collector.types import SourceResult, SwiftCollectorMeta
from database.repository import JobRepository
from integrations.telegram import send_message
from parser.activity import ActivitySummary


def _format_coverage_line(label: str, ok: int, total: int, failed_names: list[str]) -> str:
    if total == 0:
        return f"{label}: unavailable"

    if ok == total:
        return f"{label}: {total}/{total} OK"

    failed = total - ok
    names = ", ".join(failed_names[:3])
    if len(failed_names) > 3:
        names = f"{names} +{len(failed_names) - 3} more"
    return f"{label}: {ok}/{total} OK ({failed} failed: {names})"


def _render_coverage(
    swift_meta: SwiftCollectorMeta | None,
    source_results: list[SourceResult],
) -> tuple[str, bool]:
    lines: list[str] = []
    has_failures = False

    if swift_meta and swift_meta.sources_total > 0:
        lines.append(
            _format_coverage_line(
                "Companies",
                swift_meta.sources_ok,
                swift_meta.sources_total,
                swift_meta.failed_companies,
            )
        )
        if swift_meta.sources_failed > 0:
            has_failures = True

    feed_results = [result for result in source_results if result.source_id != "swift-export"]
    if feed_results:
        feed_total = len(feed_results)
        feed_failed = [result for result in feed_results if result.status == "failed"]
        feed_ok = feed_total - len(feed_failed)
        failed_names = [result.source_name for result in feed_failed]
        lines.append(_format_coverage_line("Direct feeds", feed_ok, feed_total, failed_names))
        if feed_failed:
            has_failures = True

    if not lines:
        total_sources = len(source_results)
        failed_sources = sum(1 for result in source_results if result.status == "failed")
        healthy_sources = total_sources - failed_sources
        failed_names = [result.source_name for result in source_results if result.status == "failed"]
        lines.append(_format_coverage_line("Sources", healthy_sources, total_sources, failed_names))
        has_failures = failed_sources > 0

    return "\n".join(lines), has_failures


def _render_open_roles(open_roles: int) -> str:
    if open_roles == 0:
        return "Open roles: none right now"
    if open_roles == 1:
        return "Open roles: 1 iOS vacancy"
    return f"Open roles: {open_roles} iOS vacancies"


def render_monitor_digest(
    activity: ActivitySummary,
    open_roles: int,
    tracked_total: int,
    source_results: list[SourceResult],
    swift_meta: SwiftCollectorMeta | None = None,
) -> str:
    coverage_lines, has_failures = _render_coverage(swift_meta, source_results)
    status_icon = "⚠️" if has_failures else "✅"
    checked_at = datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%d %b %Y, %H:%M")

    return f"""{status_icon} iOS Hunter

Run Activity
Actionable: {activity.actionable}
New: {activity.new}
Updated: {activity.updated}
Reopened: {activity.reopened}
Closed: {activity.closed}

{activity.headline()}

Coverage
{coverage_lines}

{_render_open_roles(open_roles)}
Tracking in total: {tracked_total}

Checked {checked_at} Kyiv"""


def send_monitor_digest(
    repo: JobRepository,
    activity: ActivitySummary,
    source_results: list[SourceResult],
    profile: dict,
    swift_meta: SwiftCollectorMeta | None = None,
) -> bool:
    if not profile.get("telegram", {}).get("enabled", True):
        return False

    message = render_monitor_digest(
        activity,
        repo.count_open_jobs(),
        repo.count_tracked_jobs(),
        source_results,
        swift_meta=swift_meta,
    )
    send_message(message)
    return True
