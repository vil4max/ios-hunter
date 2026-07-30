from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

KYIV = ZoneInfo("Europe/Kyiv")
COLLECT_HOURS = (9, 12, 15, 18)
FINAL_COLLECT_HOUR = 18
BUSINESS_HOUR_START = COLLECT_HOURS[0]
BUSINESS_HOUR_END = COLLECT_HOURS[-1]
BUSINESS_HOURS = COLLECT_HOURS


def _as_kyiv(now: datetime | None = None) -> datetime:
    stamp = now or datetime.now(KYIV)
    if stamp.tzinfo is None:
        return stamp.replace(tzinfo=KYIV)
    return stamp.astimezone(KYIV)


def is_collect_business_hour(now: datetime | None = None) -> bool:
    return _as_kyiv(now).hour in COLLECT_HOURS


def is_final_collect_slot(now: datetime | None = None) -> bool:
    return _as_kyiv(now).hour == FINAL_COLLECT_HOUR


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
