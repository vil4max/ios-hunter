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


def _sites_status_line(stats: CollectReportStats) -> str:
    failed = _site_failed_names(stats)
    total = stats.sites_total
    ok = stats.sites_ok
    if total <= 0 and not failed:
        return "✅ Поиск по сайтам: OK"
    if failed:
        shown = ", ".join(failed[:4])
        extra = f" (+{len(failed) - 4})" if len(failed) > 4 else ""
        ratio = f"{ok}/{total} " if total > 0 else ""
        return f"⚠️ Поиск по сайтам: {ratio}ошибки — {shown}{extra}"
    return f"✅ Поиск по сайтам: OK ({ok}/{total})" if total > 0 else "✅ Поиск по сайтам: OK"


def _telegram_status_line(stats: CollectReportStats) -> str:
    failed = _telegram_failed_names(stats)
    if stats.telegram_total <= 0 and stats.telegram_skipped <= 0 and not failed:
        return "⏭️ Telegram: не настроен"
    if stats.telegram_skipped > 0 and stats.telegram_ok == 0 and not failed:
        return "⏭️ Telegram: пропущен (нет session)"
    if failed:
        ratio = f"{stats.telegram_ok}/{stats.telegram_total} " if stats.telegram_total > 0 else ""
        return f"⚠️ Telegram: {ratio}ошибки"
    return f"✅ Telegram: OK ({stats.telegram_ok}/{stats.telegram_total})"


def _checks_passed(stats: CollectReportStats) -> bool:
    return not stats.failed_source_names


def _status_block(stats: CollectReportStats) -> list[str]:
    lines = [
        _sites_status_line(stats),
        _telegram_status_line(stats),
        (
            f"📊 Найдено: {stats.found} · в базе: {stats.seen_total} · новых: {stats.new_count}"
        ),
    ]
    return lines


def _system_footer(
    *,
    stats: CollectReportStats,
    board_url: str = "",
    now: datetime | None = None,
    include_board: bool = False,
) -> list[str]:
    lines: list[str] = []
    if _checks_passed(stats):
        lines.append(f"✅ Все проверки прошли · {_time_label(now)}")
    else:
        lines.append(f"⚠️ Проверки с ошибками · {_time_label(now)}")
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
        *_status_block(stats),
        "",
        *_system_footer(stats=stats, board_url=board_url, now=now, include_board=False),
    ]
    return "\n".join(blocks)


def _snippet(vacancy: Vacancy, *, limit: int = 140) -> str:
    raw = (vacancy.description or "").strip()
    if not raw:
        return ""
    title = vacancy.title.strip()
    lines: list[str] = []
    for part in raw.splitlines():
        line = " ".join(part.split()).strip()
        if not line or line == title:
            continue
        lines.append(line)
    blob = " · ".join(lines) if lines else " ".join(raw.split())
    if len(blob) <= limit:
        return blob
    return blob[: limit - 1].rstrip() + "…"


def _published_label(vacancy: Vacancy) -> str:
    if vacancy.published_at is None:
        return ""
    stamp = vacancy.published_at
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=_KYIV)
    return stamp.astimezone(_KYIV).strftime("%Y-%m-%d %H:%M")


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
        url = vacancy.url.strip()
        is_telegram = (vacancy.source or "").strip().lower() == "telegram"
        lines.append(f"{index}. {title}")
        snippet = _snippet(vacancy)
        if snippet:
            lines.append(f"   📝 {snippet}")
        if company and not (is_telegram and company.lower() in {"telegram", "itrecruit_ua", "remotejobss", "itfreelancers"}):
            if not (is_telegram and company.lower().startswith("telegram @")):
                lines.append(f"   🏢 {company}")
        if not is_telegram:
            lines.append(f"   📡 {resolve_source(vacancy)}")
        published = _published_label(vacancy)
        if published:
            lines.append(f"   📅 {published}")
        if url:
            lines.append(f"   🔗 {url}")
    lines.append("")
    lines.extend(_status_block(stats))
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
