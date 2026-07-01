from __future__ import annotations

from pathlib import Path

ALLOWED_DB_SUFFIXES = {".db", ".sqlite"}


def resolve_db_path(db_path: str | Path, base_dir: Path | None = None) -> Path:
    base = (base_dir or Path.cwd()).resolve()
    candidate = Path(db_path).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    resolved = candidate.resolve()

    if resolved.suffix.lower() not in ALLOWED_DB_SUFFIXES:
        raise ValueError(f"Unsupported database file extension: {resolved.suffix}")

    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved
