from __future__ import annotations

import asyncio
import os
import re
import time
from datetime import datetime, timezone
from typing import Any

from parser.normalize import is_ios_job

from collector.types import SourceResult

TELEGRAM_CHANNELS: tuple[str, ...] = ("itrecruit_ua",)

_LOOKBACK = 100

_CANDIDATE_MARKERS: tuple[str, ...] = (
    "#candidates",
    "#candidate",
    "#резюме",
    "#resume",
    "#cv",
    "#candidatebench",
    "looking for new opportunities",
    "looking for opportunities",
    "open to work",
    "open for opportunities",
    "ищу работу",
    "ищу роботу",
    "шукаю роботу",
    "шукаю проєкт",
    "шукаю проект",
    "available candidate",
    "propose partnership",
    "white-label",
    "outstaffing projects",
    "outsourcing & outstaffing",
)

_VACANCY_MARKERS: tuple[str, ...] = (
    "#вакансія",
    "#вакансия",
    "#vacancy",
    "#job",
    "#hiring",
    "#jobs",
    "#ios",
    "#swift",
    "вакансія",
    "вакансия",
    "we're hiring",
    "we are hiring",
    "now hiring",
    "hiring:",
    "looking for",
    "шукаємо",
    "шукає",
    "ищем",
    "ищут",
    "за деталями",
    "open role",
    "open position",
    "open positions",
)

_COMPANY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?im)^(.{2,80}?)\s+шука[єе]\b"),
    re.compile(r"(?im)^(.{2,80}?)\s+is hiring\b"),
    re.compile(r"(?im)^(.{2,80}?)\s+are hiring\b"),
    re.compile(r"(?im)^company\s*[:\-]\s*(.+)$"),
    re.compile(r"(?im)^компані[яя]\s*[:\-]\s*(.+)$"),
)


def credentials_configured() -> bool:
    return bool(
        os.environ.get("TELEGRAM_API_ID", "").strip()
        and os.environ.get("TELEGRAM_API_HASH", "").strip()
        and os.environ.get("TELEGRAM_SESSION", "").strip()
    )


def is_candidate_post(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _CANDIDATE_MARKERS)


def looks_like_vacancy(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _VACANCY_MARKERS)


def should_keep_message(text: str) -> bool:
    if not text.strip():
        return False
    if is_candidate_post(text):
        return False
    if not is_ios_job(text):
        return False
    if not looks_like_vacancy(text):
        return False
    return True


def extract_title(text: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#") and " " not in line.lstrip("#").replace("_", ""):
            continue
        if re.fullmatch(r"(?:#\w[\w+-]*\s*)+", line, flags=re.UNICODE):
            continue
        cleaned = re.sub(r"\s+", " ", line).strip(" -–—|")
        if cleaned:
            return cleaned[:160]
    return "iOS / Swift vacancy"


def extract_company(text: str) -> str | None:
    for pattern in _COMPANY_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        company = re.sub(r"\s+", " ", match.group(1)).strip(" -–—|🎯🚀⚓️")
        company = re.sub(r"^#\S+\s*", "", company).strip()
        if 2 <= len(company) <= 80:
            return company
    return None


def description_snippet(text: str, *, title: str, limit: int = 140) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if re.fullmatch(r"(?:#\w[\w+-]*\s*)+", line, flags=re.UNICODE):
            continue
        if line == title:
            continue
        lines.append(line)
    blob = " · ".join(lines) if lines else text.strip()
    blob = re.sub(r"\s+", " ", blob).strip()
    if len(blob) <= limit:
        return blob
    return blob[: limit - 1].rstrip() + "…"


def message_url(channel: str, message_id: int) -> str:
    return f"https://t.me/{channel}/{message_id}"


def job_from_message(
    channel: str,
    message_id: int,
    text: str,
    *,
    published_at: datetime | None = None,
) -> dict[str, Any] | None:
    if not should_keep_message(text):
        return None
    title = extract_title(text)
    company = extract_company(text) or "Telegram"
    return {
        "company": company,
        "title": title,
        "url": message_url(channel, message_id),
        "source": "telegram",
        "source_job_id": f"{channel}:{message_id}",
        "description": description_snippet(text, title=title, limit=4000),
        "published_at": published_at.isoformat() if published_at else None,
    }


def _source_ok(channel: str, jobs: list[dict[str, Any]], started: float) -> SourceResult:
    return SourceResult(
        source_id=f"telegram:{channel}",
        source_name=f"Telegram @{channel}",
        source_url=f"https://t.me/{channel}",
        jobs=jobs,
        status="healthy",
        error=None,
        response_ms=int((time.perf_counter() - started) * 1000),
    )


def _source_failed(channel: str, error: Exception, started: float) -> SourceResult:
    return SourceResult(
        source_id=f"telegram:{channel}",
        source_name=f"Telegram @{channel}",
        source_url=f"https://t.me/{channel}",
        jobs=[],
        status="failed",
        error=str(error),
        response_ms=int((time.perf_counter() - started) * 1000),
    )


def _source_skipped(channel: str, reason: str, started: float) -> SourceResult:
    return SourceResult(
        source_id=f"telegram:{channel}",
        source_name=f"Telegram @{channel}",
        source_url=f"https://t.me/{channel}",
        jobs=[],
        status="healthy",
        error=reason,
        response_ms=int((time.perf_counter() - started) * 1000),
    )


def _message_published_at(message: Any) -> datetime | None:
    raw = getattr(message, "date", None)
    if raw is None:
        return None
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw
    return None


async def _fetch_channel_jobs(channel: str) -> list[dict[str, Any]]:
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    api_id = int(os.environ["TELEGRAM_API_ID"].strip())
    api_hash = os.environ["TELEGRAM_API_HASH"].strip()
    session = os.environ["TELEGRAM_SESSION"].strip()

    jobs: list[dict[str, Any]] = []
    async with TelegramClient(StringSession(session), api_id, api_hash) as client:
        messages = await client.get_messages(channel, limit=_LOOKBACK)
        for message in messages:
            if message is None or not getattr(message, "id", None):
                continue
            text = (message.message or "").strip()
            if not text and getattr(message, "raw_text", None):
                text = str(message.raw_text).strip()
            job = job_from_message(
                channel,
                int(message.id),
                text,
                published_at=_message_published_at(message),
            )
            if job:
                jobs.append(job)
    return jobs


def collect_telegram_channel(channel: str) -> SourceResult:
    started = time.perf_counter()
    if not credentials_configured():
        return _source_skipped(channel, "TELEGRAM_API_ID/HASH/SESSION not set", started)
    try:
        jobs = asyncio.run(_fetch_channel_jobs(channel))
        return _source_ok(channel, jobs, started)
    except Exception as error:  # noqa: BLE001
        return _source_failed(channel, error, started)


def collect_telegram_channels(
    channels: tuple[str, ...] = TELEGRAM_CHANNELS,
) -> list[SourceResult]:
    return [collect_telegram_channel(channel) for channel in channels]
