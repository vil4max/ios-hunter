from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parser.normalize import Vacancy, canonicalize_url


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_seen_path(root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parents[1]
    return base / "database" / "seen.json"


def seen_key(vacancy: Vacancy) -> str:
    if vacancy.canonical_url:
        return vacancy.canonical_url
    return vacancy.identity_key or vacancy.hash


def load_seen(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def save_seen(path: Path, seen: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = dict(sorted(seen.items(), key=lambda item: item[0]))
    path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def mark_seen(
    seen: dict[str, dict[str, Any]],
    vacancy: Vacancy,
    *,
    first_seen: str | None = None,
) -> bool:
    key = seen_key(vacancy)
    if not key or key in seen:
        return False
    seen[key] = {
        "title": vacancy.title,
        "company": vacancy.company,
        "first_seen": first_seen or utc_now(),
    }
    return True


def migrate_from_sqlite(db_path: Path, seen: dict[str, dict[str, Any]]) -> int:
    if not db_path.exists():
        return 0

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    added = 0
    try:
        rows = connection.execute(
            """
            SELECT company, title, url, canonical_url, first_seen
            FROM jobs
            WHERE url IS NOT NULL AND TRIM(url) != ''
            """
        ).fetchall()
    except sqlite3.Error:
        connection.close()
        return 0

    for row in rows:
        url = canonicalize_url(row["canonical_url"] or row["url"] or "")
        if not url or url in seen:
            continue
        seen[url] = {
            "title": row["title"] or "",
            "company": row["company"] or "",
            "first_seen": row["first_seen"] or utc_now(),
        }
        added += 1

    connection.close()
    return added
