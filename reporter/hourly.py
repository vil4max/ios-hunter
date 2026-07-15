from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from database.seen import seen_key
from integrations.notify import CollectReportStats, resolve_source
from integrations.telegram import send_message
from parser.normalize import Vacancy
from project_sync.sync import SyncResult

_KYIV = ZoneInfo("Europe/Kyiv")


def format_hourly_heartbeat(
    *,
    stats: CollectReportStats,
    new_count: int,
    board_url: str = "",
    now: datetime | None = None,
) -> str:
    stamp = (now or datetime.now(_KYIV)).astimezone(_KYIV)
    time_label = stamp.strftime("%Y-%m-%d %H:%M")
    if new_count > 0:
        lines = [
            f"🆕 +{new_count} Inbox · {time_label}",
            "✅ Система работает",
        ]
    else:
        lines = [
            f"✅ Система работает · {time_label}",
            "📭 Новых вакансий не обнаружено",
        ]
    if stats.failed_source_names:
        lines.append(f"⚠️ ошибки: {', '.join(stats.failed_source_names)}")
    if board_url and new_count > 0:
        lines.append(f"🔗 {board_url}")
    return "\n".join(lines)


def format_hourly_new_vacancies(
    vacancies: list[Vacancy],
    *,
    stats: CollectReportStats,
    board_url: str = "",
    now: datetime | None = None,
) -> str:
    lines = [
        format_hourly_heartbeat(
            stats=stats,
            new_count=len(vacancies),
            board_url=board_url,
            now=now,
        )
    ]
    for index, vacancy in enumerate(vacancies, start=1):
        title = vacancy.title.strip()
        company = vacancy.company.strip()
        source = resolve_source(vacancy)
        url = vacancy.url.strip()
        lines.append("")
        lines.append(f"{index}. {title}")
        if company:
            lines.append(f"   🏢 {company}")
        lines.append(f"   📡 {source}")
        if url:
            lines.append(f"   🔗 {url}")
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
            new_count=0,
            board_url=board_url,
            now=now,
        )
    send_message(message)
    return True
