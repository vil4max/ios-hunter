from __future__ import annotations

from pathlib import Path

from database.daily_email_days import (
    email_sent_for_day,
    load_daily_email_days,
    mark_email_sent,
    unmark_email_sent,
)


def test_mark_and_query_daily_email_days(tmp_path: Path) -> None:
    path = tmp_path / "daily_email_days.json"
    assert email_sent_for_day(path, "2026-08-03") is False
    assert mark_email_sent(path, "2026-08-03") is True
    assert email_sent_for_day(path, "2026-08-03") is True
    assert mark_email_sent(path, "2026-08-03") is False
    assert mark_email_sent(path, "2026-08-02") is True
    data = load_daily_email_days(path)
    assert data["days"] == ["2026-08-02", "2026-08-03"]


def test_corrupt_json_resets_to_empty(tmp_path: Path) -> None:
    path = tmp_path / "daily_email_days.json"
    path.write_text("{not-json", encoding="utf-8")
    assert load_daily_email_days(path) == {"days": []}
    assert email_sent_for_day(path, "2026-08-03") is False


def test_invalid_shape_resets_to_empty(tmp_path: Path) -> None:
    path = tmp_path / "daily_email_days.json"
    path.write_text('{"days": {"oops": 1}}\n', encoding="utf-8")
    assert load_daily_email_days(path) == {"days": []}


def test_unmark_email_sent(tmp_path: Path) -> None:
    path = tmp_path / "daily_email_days.json"
    mark_email_sent(path, "2026-08-03")
    assert unmark_email_sent(path, "2026-08-03") is True
    assert email_sent_for_day(path, "2026-08-03") is False
    assert unmark_email_sent(path, "2026-08-03") is False
