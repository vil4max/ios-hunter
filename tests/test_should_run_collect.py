from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from database.collect_slots import mark_slot_completed
from scripts import should_run_collect

KYIV = ZoneInfo("Europe/Kyiv")


def test_should_run_collect_email_pending_when_slot_already_done(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    slots = tmp_path / "collect_slots.json"
    email_days = tmp_path / "daily_email_days.json"
    email_days.write_text('{"days": []}\n', encoding="utf-8")
    mark_slot_completed(slots, "2026-08-04", 18)
    monkeypatch.setenv("COLLECT_SLOTS_PATH", str(slots))
    monkeypatch.setenv("DAILY_EMAIL_DAYS_PATH", str(email_days))
    monkeypatch.setattr(
        should_run_collect,
        "_as_kyiv",
        lambda now=None: datetime(2026, 8, 4, 18, 30, tzinfo=KYIV),
    )
    monkeypatch.setattr(
        should_run_collect,
        "due_collect_slot",
        lambda now=None: 18,
    )
    monkeypatch.setattr(
        should_run_collect,
        "is_final_collect_slot",
        lambda now=None: True,
    )

    assert should_run_collect.main() == 1
    out = capsys.readouterr().out
    assert "dispatch_daily_email=true" in out
    assert "already completed" in out


def test_should_run_collect_email_not_pending_when_claimed(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    slots = tmp_path / "collect_slots.json"
    email_days = tmp_path / "daily_email_days.json"
    email_days.write_text('{"days": ["2026-08-04"]}\n', encoding="utf-8")
    monkeypatch.setenv("COLLECT_SLOTS_PATH", str(slots))
    monkeypatch.setenv("DAILY_EMAIL_DAYS_PATH", str(email_days))
    monkeypatch.setattr(
        should_run_collect,
        "_as_kyiv",
        lambda now=None: datetime(2026, 8, 4, 18, 30, tzinfo=KYIV),
    )
    monkeypatch.setattr(
        should_run_collect,
        "due_collect_slot",
        lambda now=None: 18,
    )
    monkeypatch.setattr(
        should_run_collect,
        "is_final_collect_slot",
        lambda now=None: True,
    )

    assert should_run_collect.main() == 0
    out = capsys.readouterr().out
    assert "dispatch_daily_email=false" in out
