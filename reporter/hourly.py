from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from database.seen import seen_key
from integrations.notify import CollectReportStats, SourceFailure
from integrations.telegram import TELEGRAM_MAX_LENGTH, send_message
from parser.normalize import Vacancy
from project_sync.sync import SyncResult

_KYIV = ZoneInfo("Europe/Kyiv")


def _time_label(now: datetime | None) -> str:
    stamp = (now or datetime.now(_KYIV)).astimezone(_KYIV)
    return stamp.strftime("%Y-%m-%d %H:%M")


def _telegram_failed_names(stats: CollectReportStats) -> list[str]:
    names: list[str] = []
    for name in stats.failed_source_names:
        if name.startswith("Telegram @") or name.lower().startswith("telegram"):
            names.append(name.removeprefix("Telegram @").removeprefix("Telegram ").strip() or name)
    return names


def _site_failed_names(stats: CollectReportStats) -> list[str]:
    return [
        name
        for name in stats.failed_source_names
        if not (name.startswith("Telegram @") or name.lower().startswith("telegram"))
    ]


def _failure_reason(error: str) -> str:
    lowered = error.lower()
    if "official career url unresolved" in lowered:
        return "карьерная страница не настроена"
    for status in (429, 403, 454, 455):
        if f"http {status}" in lowered or f"{status} client error" in lowered:
            if status == 429:
                return "сайт временно ограничил запросы (HTTP 429)"
            return f"сайт отклонил автоматический запрос (HTTP {status})"
    return error.strip() or "неизвестная ошибка"


def _site_failures(stats: CollectReportStats) -> list[SourceFailure]:
    return [
        failure
        for failure in stats.failed_sources
        if not (
            failure.name.startswith("Telegram @")
            or failure.name.lower().startswith("telegram")
        )
    ]


def _companies_count_label(total: int) -> str:
    n = abs(total) % 100
    n1 = n % 10
    if n1 == 1 and n != 11:
        return f"{total} компанию"
    if 2 <= n1 <= 4 and not (12 <= n <= 14):
        return f"{total} компании"
    return f"{total} компаний"


def _sites_status_line(stats: CollectReportStats) -> str:
    failed = _site_failed_names(stats)
    if not failed:
        return "✅ Поиск по сайтам: OK"
    details = _site_failures(stats)
    if not details:
        return f"⚠️ Поиск по сайтам: {', '.join(failed)}"
    lines = [f"⚠️ Не удалось проверить {_companies_count_label(len(details))}"]
    for failure in details:
        lines.append(f"• {failure.name} — {_failure_reason(failure.reason)}")
        if failure.url:
            lines.append(f"  {failure.url}")
    return "\n".join(lines)


def _telegram_status_line(stats: CollectReportStats) -> str:
    failed = _telegram_failed_names(stats)
    if stats.telegram_total <= 0 and stats.telegram_skipped <= 0 and not failed:
        return "⏭️ Telegram: не настроен"
    if stats.telegram_skipped > 0 and stats.telegram_ok == 0 and not failed:
        return "⏭️ Telegram: пропущен (нет session)"
    if failed:
        shown = ", ".join(failed[:4])
        extra = f" (+{len(failed) - 4})" if len(failed) > 4 else ""
        return f"⚠️ Telegram: {shown}{extra}"
    return "✅ Telegram: OK"


_HEALTHY_STATUS = "🟢 Система в порядке"


def _new_vacancies_header(total: int) -> str:
    """Title line for new-vacancy alerts: emoji + count + Russian noun form."""
    n = abs(total) % 100
    n1 = n % 10
    if n1 == 1 and n != 11:
        word = "новая вакансия"
    elif 2 <= n1 <= 4 and not (12 <= n <= 14):
        word = "новые вакансии"
    else:
        word = "новых вакансий"
    return f"📬 +{total} {word}"


def _degraded_status_line(stats: CollectReportStats) -> str | None:
    if not stats.degraded_source_names:
        return None
    shown = ", ".join(stats.degraded_source_names[:4])
    extra = (
        f" (+{len(stats.degraded_source_names) - 4})"
        if len(stats.degraded_source_names) > 4
        else ""
    )
    return f"⚠️ Источники без результата: {shown}{extra}"


def _collect_status_lines(stats: CollectReportStats) -> list[str]:
    lines: list[str] = []
    if _site_failed_names(stats):
        lines.append(_sites_status_line(stats))
    degraded = _degraded_status_line(stats)
    if degraded:
        lines.append(degraded)
    if _telegram_failed_names(stats):
        lines.append(_telegram_status_line(stats))
    if not lines:
        lines.append(_HEALTHY_STATUS)
    return lines


def _status_block(stats: CollectReportStats, now: datetime | None = None) -> list[str]:
    stamp = _time_label(now)
    status = _collect_status_lines(stats)
    if len(status) == 1 and status[0] == _HEALTHY_STATUS:
        return [f"{_HEALTHY_STATUS} · {stamp}"]
    return [*status, f"🕐 {stamp}"]


def _footer(
    *,
    stats: CollectReportStats,
    board_url: str = "",
    now: datetime | None = None,
    include_board: bool = False,
) -> list[str]:
    lines = list(_status_block(stats, now))
    if include_board and board_url:
        lines.append(f"🔗 {board_url}")
    return lines


def _vacancy_label(vacancy: Vacancy) -> str:
    title = vacancy.title.strip()
    company = vacancy.company.strip()
    is_telegram = (vacancy.source or "").strip().lower() == "telegram"
    skip_company = is_telegram and company.lower() in {
        "telegram",
        "itrecruit_ua",
        "remotejobss",
        "itfreelancers",
        "mobile_jobs",
    }
    if company and not skip_company and not (is_telegram and company.lower().startswith("telegram @")):
        return f"{company} — {title}" if title else company
    return title or company or vacancy.url.strip()


def format_hourly_heartbeat(
    *,
    stats: CollectReportStats,
    new_count: int = 0,
    board_url: str = "",
    now: datetime | None = None,
    live: list[Vacancy] | None = None,
) -> str:
    _ = new_count
    _ = board_url
    _ = live
    lines = ["📭 Новых вакансий нет", "", *_status_block(stats, now)]
    return "\n".join(lines)


def format_hourly_new_vacancies(
    vacancies: list[Vacancy],
    *,
    stats: CollectReportStats,
    board_url: str = "",
    now: datetime | None = None,
    total_count: int | None = None,
    part: int | None = None,
    parts: int | None = None,
    index_offset: int = 0,
) -> str:
    total = total_count if total_count is not None else len(vacancies)
    header = _new_vacancies_header(total)
    if part is not None and parts is not None and parts > 1:
        header = f"{header} ({part}/{parts})"
    lines = [header, ""]
    for index, vacancy in enumerate(vacancies, start=1):
        display_index = index_offset + index
        lines.append(f"{display_index}. {_vacancy_label(vacancy)}")
        url = vacancy.url.strip()
        if url:
            lines.append(f"   {url}")
    lines.append("")
    lines.extend(
        _footer(
            stats=stats,
            board_url=board_url,
            now=now,
            include_board=False,
        )
    )
    return "\n".join(lines)


def _pack_vacancy_batches(
    vacancies: list[Vacancy],
    *,
    stats: CollectReportStats,
    board_url: str = "",
    now: datetime | None = None,
    limit: int | None = None,
) -> list[str]:
    if not vacancies:
        return []
    max_len = TELEGRAM_MAX_LENGTH if limit is None else limit
    total = len(vacancies)
    batches: list[list[Vacancy]] = []
    current: list[Vacancy] = []
    offset = 0
    for vacancy in vacancies:
        candidate = current + [vacancy]
        message = format_hourly_new_vacancies(
            candidate,
            stats=stats,
            board_url=board_url,
            now=now,
            total_count=total,
            part=1,
            parts=99,
            index_offset=offset,
        )
        if current and len(message) > max_len:
            batches.append(current)
            offset += len(current)
            current = [vacancy]
        else:
            current = candidate
    if current:
        batches.append(current)

    parts = len(batches)
    messages: list[str] = []
    index_offset = 0
    for part_index, batch in enumerate(batches, start=1):
        messages.append(
            format_hourly_new_vacancies(
                batch,
                stats=stats,
                board_url=board_url,
                now=now,
                total_count=total,
                part=part_index,
                parts=parts,
                index_offset=index_offset,
            )
        )
        index_offset += len(batch)
    return messages


def vacancies_for_alert(sync_result: SyncResult, fresh: list[Vacancy]) -> list[Vacancy]:
    if not fresh:
        return []
    if sync_result.skipped_disabled:
        return list(fresh)
    alert_keys = {
        item.canonical_url
        for item in (*sync_result.created, *sync_result.existing)
        if item.canonical_url
    }
    if not alert_keys:
        return []
    return [vacancy for vacancy in fresh if seen_key(vacancy) in alert_keys]


def notify_hourly_inbox(
    sync_result: SyncResult,
    fresh: list[Vacancy],
    *,
    stats: CollectReportStats,
    board_url: str = "",
    now: datetime | None = None,
    live: list[Vacancy] | None = None,
    excluded_urls: set[str] | frozenset[str] | None = None,
) -> bool:
    _ = live
    _ = excluded_urls
    to_show = vacancies_for_alert(sync_result, fresh)
    if to_show:
        for message in _pack_vacancy_batches(
            to_show,
            stats=stats,
            board_url=board_url,
            now=now,
        ):
            send_message(message)
    else:
        send_message(
            format_hourly_heartbeat(
                stats=stats,
                board_url=board_url,
                now=now,
            )
        )
    return True
