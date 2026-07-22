from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Any

from parser.normalize import is_ios_job

from collector.types import SourceResult

TELEGRAM_CHANNELS: tuple[str, ...] = ("itrecruit_ua",)

_LOOKBACK = 100

_CANDIDATE_MARKERS: tuple[str, ...] = (
    "#candidates",
    "#candidate",
    "#резюме",
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
)

_VACANCY_MARKERS: tuple[str, ...] = (
    "#вакансія",
    "#вакансия",
    "#vacancy",
    "#job",
    "#hiring",
    "#jobs",
    "вакансія",
    "вакансия",
    "looking for",
    "шукаємо",
    "ищем",
    "за деталями",
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
    if not is_ios_job(text):
        return False
    if is_candidate_post(text):
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


def message_url(channel: str, message_id: int) -> str:
    return f"https://t.me/{channel}/{message_id}"


def job_from_message(channel: str, message_id: int, text: str) -> dict[str, Any] | None:
    if not should_keep_message(text):
        return None
    return {
        "company": f"Telegram @{channel}",
        "title": extract_title(text),
        "url": message_url(channel, message_id),
        "source": "telegram",
        "source_job_id": f"{channel}:{message_id}",
        "description": text.strip()[:4000],
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
            job = job_from_message(channel, int(message.id), text)
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
