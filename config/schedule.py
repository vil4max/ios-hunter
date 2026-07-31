from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

KYIV = ZoneInfo("Europe/Kyiv")
COLLECT_HOURS = (9, 12, 15, 18)
FINAL_COLLECT_HOUR = 18
COLLECT_KICK_LAG_MINUTES = 15
BUSINESS_HOUR_START = COLLECT_HOURS[0]
BUSINESS_HOUR_END = COLLECT_HOURS[-1]
BUSINESS_HOURS = COLLECT_HOURS


def _as_kyiv(now: datetime | None = None) -> datetime:
    stamp = now or datetime.now(KYIV)
    if stamp.tzinfo is None:
        return stamp.replace(tzinfo=KYIV)
    return stamp.astimezone(KYIV)


def due_collect_slot(now: datetime | None = None) -> int | None:
    """Latest Kyiv collect hour that has already started today.

    Used as catch-up for GitHub Actions schedule lag: after 09:00 and before
    12:00 the due slot stays 9 so a late cron can still dispatch collect.
    """
    stamp = _as_kyiv(now)
    due: int | None = None
    for hour in COLLECT_HOURS:
        start = datetime(stamp.year, stamp.month, stamp.day, hour, 0, tzinfo=KYIV)
        if stamp >= start:
            due = hour
    return due


def due_collect_slot_for_local_kick(now: datetime | None = None) -> int | None:
    """Due slot only after COLLECT_KICK_LAG_MINUTES past slot start (local GHA lag kick)."""
    stamp = _as_kyiv(now)
    due = due_collect_slot(stamp)
    if due is None:
        return None
    ready_at = datetime(
        stamp.year, stamp.month, stamp.day, due, 0, tzinfo=KYIV
    ) + timedelta(minutes=COLLECT_KICK_LAG_MINUTES)
    if stamp < ready_at:
        return None
    return due


def is_collect_business_hour(now: datetime | None = None) -> bool:
    return due_collect_slot(now) is not None


def is_final_collect_slot(now: datetime | None = None) -> bool:
    return due_collect_slot(now) == FINAL_COLLECT_HOUR


def next_scheduled_collect(now: datetime | None = None) -> datetime:
    stamp = _as_kyiv(now)
    day = stamp.date()
    for _ in range(3):
        for hour in COLLECT_HOURS:
            candidate = datetime(day.year, day.month, day.day, hour, 0, tzinfo=KYIV)
            if candidate > stamp:
                return candidate
        day = day + timedelta(days=1)
    raise RuntimeError("no collect slot found")


def format_next_check_line(now: datetime | None = None) -> str:
    stamp = _as_kyiv(now)
    nxt = next_scheduled_collect(stamp)
    clock = f"{nxt.hour}:00"
    if nxt.date() == stamp.date():
        return f"⏭ Следующая проверка в {clock}"
    if nxt.date() == stamp.date() + timedelta(days=1):
        return f"⏭ Следующая проверка завтра в {clock}"
    return f"⏭ Следующая проверка {nxt.strftime('%Y-%m-%d')} в {clock}"
