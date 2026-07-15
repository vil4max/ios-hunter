from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from integrations.notify import CollectReportStats, format_run_stats
from integrations.telegram import send_message
from project_sync.sync import SyncResult

_KYIV = ZoneInfo("Europe/Kyiv")


def format_hourly_inbox_alert(
    *,
    created_count: int,
    board_url: str = "",
    stats: CollectReportStats | None = None,
    now: datetime | None = None,
) -> str:
    stamp = (now or datetime.now(_KYIV)).astimezone(_KYIV)
    header = f"Inbox +{created_count} · {stamp.strftime('%Y-%m-%d %H:%M')}"
    lines = [header, f"Новых карточек: {created_count}"]
    if board_url:
        lines.append(board_url)
    if stats is not None:
        lines.append("")
        lines.append(format_run_stats(stats))
    return "\n".join(lines)


def notify_hourly_inbox(
    sync_result: SyncResult,
    *,
    stats: CollectReportStats,
    board_url: str = "",
    now: datetime | None = None,
) -> None:
    message = format_hourly_inbox_alert(
        created_count=sync_result.created_count,
        board_url=board_url,
        stats=stats,
        now=now,
    )
    send_message(message)
