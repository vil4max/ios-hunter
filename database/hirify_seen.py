from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from database.seen import utc_now


def default_hirify_seen_path(root: Path | None = None) -> Path:
    override = os.environ.get("HIRIFY_SEEN_PATH", "").strip()
    if override:
        return Path(override)
    base = root or Path(__file__).resolve().parents[1]
    return base / "database" / "hirify_seen.json"


def load_hirify_seen(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def save_hirify_seen(path: Path, seen: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = dict(sorted(seen.items(), key=lambda item: item[0]))
    path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def is_processed(seen: dict[str, dict[str, Any]], fingerprint: str) -> bool:
    key = (fingerprint or "").strip()
    return bool(key) and key in seen


def mark_processed(
    seen: dict[str, dict[str, Any]],
    fingerprint: str,
    *,
    stage: str,
    item_id: str | None = None,
    company: str = "",
    action: str = "",
) -> bool:
    key = (fingerprint or "").strip()
    if not key or key in seen:
        return False
    record: dict[str, Any] = {
        "stage": stage,
        "processed_at": utc_now(),
    }
    if item_id:
        record["item_id"] = item_id
    if company:
        record["company"] = company
    if action:
        record["action"] = action
    seen[key] = record
    return True
