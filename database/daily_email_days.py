from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def default_daily_email_days_path(root: Path | None = None) -> Path:
    override = os.environ.get("DAILY_EMAIL_DAYS_PATH", "").strip()
    if override:
        return Path(override)
    base = root or Path(__file__).resolve().parents[1]
    return base / "database" / "daily_email_days.json"


def load_daily_email_days(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"days": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"days": []}
    if not isinstance(data, dict):
        return {"days": []}
    days = data.get("days")
    if not isinstance(days, list):
        return {"days": []}
    return {"days": [str(day) for day in days if str(day).strip()]}


def save_daily_email_days(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    days = data.get("days") if isinstance(data.get("days"), list) else []
    ordered = sorted({str(day) for day in days if str(day).strip()})
    payload = {"days": ordered}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def email_sent_for_day(path: Path, day: str) -> bool:
    data = load_daily_email_days(path)
    days = data.get("days") or []
    return str(day) in {str(value) for value in days}


def mark_email_sent(path: Path, day: str) -> bool:
    data = load_daily_email_days(path)
    days = {str(value) for value in (data.get("days") or [])}
    if str(day) in days:
        return False
    days.add(str(day))
    data["days"] = sorted(days)
    save_daily_email_days(path, data)
    return True


def unmark_email_sent(path: Path, day: str) -> bool:
    data = load_daily_email_days(path)
    days = {str(value) for value in (data.get("days") or [])}
    if str(day) not in days:
        return False
    days.remove(str(day))
    data["days"] = sorted(days)
    save_daily_email_days(path, data)
    return True
