from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from integrations.telegram import send_message
from parser.normalize import Vacancy, canonicalize_url

_KYIV = ZoneInfo("Europe/Kyiv")

_SOURCE_BY_HOST_SUFFIX: tuple[tuple[str, str], ...] = (
    ("ashbyhq.com", "Ashby"),
    ("greenhouse.io", "Greenhouse"),
    ("lever.co", "Lever"),
    ("myworkdayjobs.com", "Workday"),
    ("workable.com", "Workable"),
    ("teamtailor.com", "Teamtailor"),
    ("breezy.hr", "Breezy"),
    ("dou.ua", "DOU"),
    ("djinni.co", "Djinni"),
    ("careers.epam.com", "EPAM careers"),
    ("dataart.team", "DataArt careers"),
    ("dataart.com", "DataArt careers"),
    ("globallogic.com", "GlobalLogic careers"),
)

_SOURCE_BY_RAW: dict[str, str] = {
    "dou": "DOU",
    "djinni": "Djinni",
    "linkedin": "LinkedIn",
    "ashby": "Ashby",
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "workable": "Workable",
    "teamtailor": "Teamtailor",
    "breezy": "Breezy",
    "workday": "Workday",
    "telegram": "Telegram",
}


@dataclass(frozen=True)
class CollectReportStats:
    found: int
    seen_total: int
    new_count: int
    duplicates_removed: int
    failed_source_names: tuple[str, ...] = ()
    sites_ok: int = 0
    sites_total: int = 0
    telegram_ok: int = 0
    telegram_total: int = 0
    telegram_skipped: int = 0
    telegram_ok_names: tuple[str, ...] = ()


def resolve_source(vacancy: Vacancy) -> str:
    raw = (vacancy.source or "").strip()
    mapped = _SOURCE_BY_RAW.get(raw.lower())
    if mapped:
        return mapped

    host = (urlsplit(vacancy.url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]

    for suffix, label in _SOURCE_BY_HOST_SUFFIX:
        if host == suffix or host.endswith("." + suffix):
            return label

    company = (vacancy.company or "").strip()
    if company:
        return f"{company} careers"
    if raw and raw.lower() != "company":
        return raw
    return "company career page"


def _dedupe_vacancies(vacancies: list[Vacancy]) -> list[Vacancy]:
    seen: set[str] = set()
    unique: list[Vacancy] = []
    for vacancy in vacancies:
        key = canonicalize_url(vacancy.url) or vacancy.url.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(vacancy)
    return unique


def format_run_stats(stats: CollectReportStats) -> str:
    lines = [
        f"Сейчас найдено: {stats.found}",
        f"Уже в базе: {stats.seen_total}",
        f"Новых: {stats.new_count}",
        "",
        f"Дубликаты сняты: {stats.duplicates_removed}",
        f"Источники с ошибкой: {len(stats.failed_source_names)}",
    ]
    for name in stats.failed_source_names:
        lines.append(f"· {name}")
    if stats.new_count == 0 and stats.found > 0:
        lines.extend(["", "Все найденные URL уже есть в базе"])
    return "\n".join(lines)


def format_vacancies_message(
    vacancies: list[Vacancy],
    *,
    now: datetime | None = None,
    stats: CollectReportStats | None = None,
) -> str | None:
    unique = _dedupe_vacancies(vacancies)
    if not unique:
        return None

    stamp = (now or datetime.now(_KYIV)).astimezone(_KYIV)
    header = f"Вакансий {len(unique)} · {stamp.strftime('%Y-%m-%d %H:%M')}"
    blocks: list[str] = [header]
    for index, vacancy in enumerate(unique, start=1):
        title = vacancy.title.strip()
        company = vacancy.company.strip()
        source = resolve_source(vacancy)
        url = vacancy.url.strip()
        blocks.append(f"{index}. {title}\n   {company}\n   {source}\n   {url}")
    message = "\n\n".join(blocks)
    if stats is not None:
        message = f"{message}\n\n{format_run_stats(stats)}"
    return message


def format_empty_report(
    *,
    stats: CollectReportStats,
    now: datetime | None = None,
) -> str:
    stamp = (now or datetime.now(_KYIV)).astimezone(_KYIV)
    return (
        f"Новых вакансий нет · {stamp.strftime('%Y-%m-%d %H:%M')}\n"
        f"\n"
        f"{format_run_stats(stats)}"
    )


def notify_new_vacancies(
    vacancies: list[Vacancy],
    *,
    now: datetime | None = None,
    stats: CollectReportStats | None = None,
) -> int:
    message = format_vacancies_message(vacancies, now=now, stats=stats)
    if message is None:
        return 0
    send_message(message)
    return len(_dedupe_vacancies(vacancies))


def notify_empty_report(
    *,
    stats: CollectReportStats,
    now: datetime | None = None,
) -> None:
    send_message(format_empty_report(stats=stats, now=now))
