from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

KYIV = ZoneInfo("Europe/Kyiv")
BUSINESS_HOUR_START = 9
BUSINESS_HOUR_END = 18
BUSINESS_HOURS = range(BUSINESS_HOUR_START, BUSINESS_HOUR_END + 1)


def _as_kyiv(now: datetime | None = None) -> datetime:
    stamp = now or datetime.now(KYIV)
    if stamp.tzinfo is None:
        return stamp.replace(tzinfo=KYIV)
    return stamp.astimezone(KYIV)


def is_collect_business_hour(now: datetime | None = None) -> bool:
    return _as_kyiv(now).hour in BUSINESS_HOURS


def next_scheduled_collect(now: datetime | None = None) -> datetime:
    stamp = _as_kyiv(now)
    day = stamp.date()
    for _ in range(3):
        for hour in BUSINESS_HOURS:
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
