from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from config.schedule import (
    format_next_check_line,
    is_collect_business_hour,
    is_final_collect_slot,
    next_scheduled_collect,
)

_KYIV = ZoneInfo("Europe/Kyiv")


def test_is_collect_business_hour_window() -> None:
    assert is_collect_business_hour(datetime(2026, 7, 28, 2, 0, tzinfo=_KYIV)) is False
    assert is_collect_business_hour(datetime(2026, 7, 28, 9, 0, tzinfo=_KYIV)) is True
    assert is_collect_business_hour(datetime(2026, 7, 28, 10, 30, tzinfo=_KYIV)) is False
    assert is_collect_business_hour(datetime(2026, 7, 28, 12, 0, tzinfo=_KYIV)) is True
    assert is_collect_business_hour(datetime(2026, 7, 28, 15, 0, tzinfo=_KYIV)) is True
    assert is_collect_business_hour(datetime(2026, 7, 28, 18, 0, tzinfo=_KYIV)) is True
    assert is_collect_business_hour(datetime(2026, 7, 28, 19, 0, tzinfo=_KYIV)) is False


def test_is_final_collect_slot() -> None:
    assert is_final_collect_slot(datetime(2026, 7, 28, 15, 0, tzinfo=_KYIV)) is False
    assert is_final_collect_slot(datetime(2026, 7, 28, 18, 0, tzinfo=_KYIV)) is True


def test_next_scheduled_collect_same_day() -> None:
    now = datetime(2026, 7, 28, 9, 21, tzinfo=_KYIV)
    assert next_scheduled_collect(now) == datetime(2026, 7, 28, 12, 0, tzinfo=_KYIV)
    assert format_next_check_line(now) == "⏭ Следующая проверка в 12:00"


def test_next_scheduled_collect_after_noon() -> None:
    now = datetime(2026, 7, 28, 12, 10, tzinfo=_KYIV)
    assert next_scheduled_collect(now) == datetime(2026, 7, 28, 15, 0, tzinfo=_KYIV)
    assert format_next_check_line(now) == "⏭ Следующая проверка в 15:00"


def test_next_scheduled_collect_last_slot() -> None:
    now = datetime(2026, 7, 28, 15, 10, tzinfo=_KYIV)
    assert next_scheduled_collect(now) == datetime(2026, 7, 28, 18, 0, tzinfo=_KYIV)
    assert format_next_check_line(now) == "⏭ Следующая проверка в 18:00"


def test_next_scheduled_collect_after_window() -> None:
    now = datetime(2026, 7, 28, 18, 5, tzinfo=_KYIV)
    assert next_scheduled_collect(now) == datetime(2026, 7, 29, 9, 0, tzinfo=_KYIV)
    assert format_next_check_line(now) == "⏭ Следующая проверка завтра в 9:00"


def test_next_scheduled_collect_before_window() -> None:
    now = datetime(2026, 7, 28, 2, 0, tzinfo=_KYIV)
    assert next_scheduled_collect(now) == datetime(2026, 7, 28, 9, 0, tzinfo=_KYIV)
    assert format_next_check_line(now) == "⏭ Следующая проверка в 9:00"
