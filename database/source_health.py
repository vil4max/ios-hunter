from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from collector.types import STATUS_DEGRADED, STATUS_FAILED, STATUS_HEALTHY, SourceResult


def default_baseline_path(root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parents[1]
    return base / "database" / "source_baseline.json"


def load_baseline(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def save_baseline(path: Path, baseline: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = dict(sorted(baseline.items(), key=lambda item: item[0]))
    path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def best_scanned(baseline: dict[str, dict[str, Any]], source_id: str) -> int:
    record = baseline.get(source_id) or {}
    try:
        return int(record.get("best_scanned", 0) or 0)
    except (TypeError, ValueError):
        return 0


def classify_degraded(
    results: list[SourceResult],
    baseline: dict[str, dict[str, Any]],
) -> list[str]:
    """Downgrade sources that used to return items but now return none.

    A collector that parses zero items while its baseline proves it once parsed
    many is almost always a broken selector, not an empty job board.
    """
    degraded: list[str] = []
    for result in results:
        if result.status != STATUS_HEALTHY or result.items_scanned > 0:
            continue
        if best_scanned(baseline, result.source_id) <= 0:
            continue
        result.status = STATUS_DEGRADED
        result.error = result.error or "parsed 0 items but previously parsed items"
        degraded.append(result.source_name)
    return degraded


def update_baseline(
    baseline: dict[str, dict[str, Any]],
    results: list[SourceResult],
    *,
    now: str | None = None,
) -> dict[str, dict[str, Any]]:
    stamp = now or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    updated = dict(baseline)
    for result in results:
        if result.status == STATUS_FAILED:
            continue
        record = dict(updated.get(result.source_id) or {})
        record["name"] = result.source_name
        record["best_scanned"] = max(best_scanned(baseline, result.source_id), result.items_scanned)
        record["last_scanned"] = result.items_scanned
        if result.items_scanned > 0:
            record["last_nonzero"] = stamp
        updated[result.source_id] = record
    return updated
