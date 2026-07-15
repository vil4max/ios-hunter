from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from database.seen import seen_key
from integrations.notify import CollectReportStats, resolve_source
from integrations.telegram import send_message
from parser.normalize import Vacancy
from project_sync.sync import SyncResult

_KYIV = ZoneInfo("Europe/Kyiv")


def format_hourly_new_vacancies(
    vacancies: list[Vacancy],
    *,
    stats: CollectReportStats,
    board_url: str = "",
    now: datetime | None = None,
) -> str | None:
    if not vacancies:
        return None

    stamp = (now or datetime.now(_KYIV)).astimezone(_KYIV)
    lines = [
        f"{stamp.strftime('%Y-%m-%d %H:%M')} · OK · +{len(vacancies)} Inbox",
        f"найдено {stats.found} · в базе {stats.seen_total}",
    ]
    if stats.failed_source_names:
        lines.append(f"ошибки: {', '.join(stats.failed_source_names)}")
    if board_url:
        lines.append(board_url)

    for index, vacancy in enumerate(vacancies, start=1):
        title = vacancy.title.strip()
        company = vacancy.company.strip()
        source = resolve_source(vacancy)
        url = vacancy.url.strip()
        lines.append("")
        lines.append(f"{index}. {title}")
        if company:
            lines.append(f"   {company}")
        lines.append(f"   {source}")
        if url:
            lines.append(f"   {url}")

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
    message = format_hourly_new_vacancies(
        to_show,
        stats=stats,
        board_url=board_url,
        now=now,
    )
    if message is None:
        return False
    send_message(message)
    return True
