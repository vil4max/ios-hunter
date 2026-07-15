from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from database.seen import seen_key
from integrations.notify import CollectReportStats, resolve_source
from integrations.telegram import send_message
from parser.normalize import Vacancy
from project_sync.sync import SyncResult

_KYIV = ZoneInfo("Europe/Kyiv")


def _time_label(now: datetime | None) -> str:
    stamp = (now or datetime.now(_KYIV)).astimezone(_KYIV)
    return stamp.strftime("%Y-%m-%d %H:%M")


def _system_footer(
    *,
    stats: CollectReportStats,
    board_url: str = "",
    now: datetime | None = None,
    include_board: bool = False,
) -> list[str]:
    lines: list[str] = []
    if stats.failed_source_names:
        lines.append(f"⚠️ ошибки: {', '.join(stats.failed_source_names)}")
        lines.append("")
    lines.append(f"✅ Система работает · {_time_label(now)}")
    if include_board and board_url:
        lines.append(f"🔗 {board_url}")
    return lines


def format_hourly_heartbeat(
    *,
    stats: CollectReportStats,
    new_count: int = 0,
    board_url: str = "",
    now: datetime | None = None,
) -> str:
    _ = new_count
    blocks = [
        "📭 Новых вакансий не обнаружено",
        "",
        *_system_footer(stats=stats, board_url=board_url, now=now, include_board=False),
    ]
    return "\n".join(blocks)


def format_hourly_new_vacancies(
    vacancies: list[Vacancy],
    *,
    stats: CollectReportStats,
    board_url: str = "",
    now: datetime | None = None,
) -> str:
    lines = [f"🆕 +{len(vacancies)} Inbox", ""]
    for index, vacancy in enumerate(vacancies, start=1):
        if index > 1:
            lines.append("")
        title = vacancy.title.strip()
        company = vacancy.company.strip()
        source = resolve_source(vacancy)
        url = vacancy.url.strip()
        lines.append(f"{index}. {title}")
        if company:
            lines.append(f"   🏢 {company}")
        lines.append(f"   📡 {source}")
        if url:
            lines.append(f"   🔗 {url}")
    lines.append("")
    lines.extend(
        _system_footer(
            stats=stats,
            board_url=board_url,
            now=now,
            include_board=True,
        )
    )
    return "\n".join(lines)


def vacancies_for_alert(sync_result: SyncResult, fresh: list[Vacancy]) -> list[Vacancy]:
    if not fresh:
        return []
    if sync_result.skipped_disabled:
        return list(fresh)
    created_keys = {item.canonical_url for item in sync_result.created if item.canonical_url}
    if not created_keys:
        return []
    return [vacancy for vacancy in fresh if seen_key(vacancy) in created_keys]


def notify_hourly_inbox(
    sync_result: SyncResult,
    fresh: list[Vacancy],
    *,
    stats: CollectReportStats,
    board_url: str = "",
    now: datetime | None = None,
) -> bool:
    to_show = vacancies_for_alert(sync_result, fresh)
    if to_show:
        message = format_hourly_new_vacancies(
            to_show,
            stats=stats,
            board_url=board_url,
            now=now,
        )
    else:
        message = format_hourly_heartbeat(
            stats=stats,
            board_url=board_url,
            now=now,
        )
    send_message(message)
    return True
