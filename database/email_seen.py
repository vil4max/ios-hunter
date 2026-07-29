from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from database.seen import utc_now


def default_email_seen_path(root: Path | None = None) -> Path:
    override = os.environ.get("EMAIL_SEEN_PATH", "").strip()
    if override:
        return Path(override)
    base = root or Path(__file__).resolve().parents[1]
    return base / "database" / "email_seen.json"


def load_email_seen(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def save_email_seen(path: Path, seen: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = dict(sorted(seen.items(), key=lambda item: item[0]))
    path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def is_processed(seen: dict[str, dict[str, Any]], message_id: str) -> bool:
    key = (message_id or "").strip()
    return bool(key) and key in seen


def mark_processed(
    seen: dict[str, dict[str, Any]],
    message_id: str,
    *,
    kind: str,
    item_id: str | None = None,
    company: str = "",
    subject: str = "",
) -> bool:
    key = (message_id or "").strip()
    if not key or key in seen:
        return False
    record: dict[str, Any] = {
        "kind": kind,
        "processed_at": utc_now(),
    }
    if item_id:
        record["item_id"] = item_id
    if company:
        record["company"] = company
    if subject:
        record["subject"] = subject[:200]
    seen[key] = record
    return True
