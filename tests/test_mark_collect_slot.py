from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts import mark_collect_slot

KYIV = ZoneInfo("Europe/Kyiv")


def test_mark_collect_slot_dispatches_email_on_final_slot(
    tmp_path: Path, monkeypatch
) -> None:
    slots = tmp_path / "collect_slots.json"
    email_days = tmp_path / "daily_email_days.json"
    email_days.write_text('{"days": []}\n', encoding="utf-8")
    output = tmp_path / "github_output.txt"
    monkeypatch.setenv("COLLECT_SLOTS_PATH", str(slots))
    monkeypatch.setenv("DAILY_EMAIL_DAYS_PATH", str(email_days))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(
        mark_collect_slot,
        "_as_kyiv",
        lambda now=None: datetime(2026, 8, 4, 18, 20, tzinfo=KYIV),
    )

    assert mark_collect_slot.main() == 0
    text = output.read_text(encoding="utf-8")
    assert "marked_slot=18" in text
    assert "final_slot=true" in text
    assert "dispatch_daily_email=true" in text


def test_mark_collect_slot_skips_email_when_already_claimed(
    tmp_path: Path, monkeypatch
) -> None:
    slots = tmp_path / "collect_slots.json"
    email_days = tmp_path / "daily_email_days.json"
    email_days.write_text('{"days": ["2026-08-04"]}\n', encoding="utf-8")
    output = tmp_path / "github_output.txt"
    monkeypatch.setenv("COLLECT_SLOTS_PATH", str(slots))
    monkeypatch.setenv("DAILY_EMAIL_DAYS_PATH", str(email_days))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(
        mark_collect_slot,
        "_as_kyiv",
        lambda now=None: datetime(2026, 8, 4, 18, 20, tzinfo=KYIV),
    )

    assert mark_collect_slot.main() == 0
    text = output.read_text(encoding="utf-8")
    assert "final_slot=true" in text
    assert "dispatch_daily_email=false" in text


def test_mark_collect_slot_non_final_does_not_dispatch_email(
    tmp_path: Path, monkeypatch
) -> None:
    slots = tmp_path / "collect_slots.json"
    email_days = tmp_path / "daily_email_days.json"
    email_days.write_text('{"days": []}\n', encoding="utf-8")
    output = tmp_path / "github_output.txt"
    monkeypatch.setenv("COLLECT_SLOTS_PATH", str(slots))
    monkeypatch.setenv("DAILY_EMAIL_DAYS_PATH", str(email_days))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(
        mark_collect_slot,
        "_as_kyiv",
        lambda now=None: datetime(2026, 8, 4, 15, 20, tzinfo=KYIV),
    )

    assert mark_collect_slot.main() == 0
    text = output.read_text(encoding="utf-8")
    assert "marked_slot=15" in text
    assert "final_slot=false" in text
    assert "dispatch_daily_email=false" in text
