from __future__ import annotations

import sqlite3
from pathlib import Path

from database.seen import load_seen, mark_seen, migrate_from_sqlite, purge_dead_seen, save_seen, seen_key
from tests.conftest import make_vacancy


def test_seen_key_prefers_canonical_url() -> None:
    vacancy = make_vacancy(url="https://Example.com/jobs/1/?utm_source=x")
    assert seen_key(vacancy) == "https://example.com/jobs/1"


def test_mark_seen_persists_and_skips_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "seen.json"
    vacancy = make_vacancy()
    seen: dict = {}

    assert mark_seen(seen, vacancy, first_seen="2026-07-10T10:00:00+00:00") is True
    assert mark_seen(seen, vacancy) is False
    save_seen(path, seen)

    reloaded = load_seen(path)
    assert seen_key(vacancy) in reloaded
    assert reloaded[seen_key(vacancy)]["title"] == vacancy.title
    assert reloaded[seen_key(vacancy)]["company"] == vacancy.company


def test_purge_dead_seen_removes_only_missing_for_purgeable_companies() -> None:
    seen = {
        "https://example.com/epam/live": {
            "title": "Senior iOS",
            "company": "EPAM",
            "first_seen": "2026-07-01T00:00:00+00:00",
        },
        "https://example.com/epam/dead": {
            "title": "Middle iOS",
            "company": "EPAM",
            "first_seen": "2026-07-01T00:00:00+00:00",
        },
        "https://example.com/softserve/old": {
            "title": "iOS Engineer",
            "company": "SoftServe",
            "first_seen": "2026-07-01T00:00:00+00:00",
        },
    }
    removed = purge_dead_seen(
        seen,
        live_urls={"https://example.com/epam/live"},
        purgeable_companies={"EPAM"},
    )
    assert removed == ["https://example.com/epam/dead"]
    assert "https://example.com/epam/live" in seen
    assert "https://example.com/softserve/old" in seen
    assert "https://example.com/epam/dead" not in seen


def test_migrate_from_sqlite_imports_urls(tmp_path: Path) -> None:
    db_path = tmp_path / "jobs.db"
    connection = sqlite3.connect(str(db_path))
    connection.execute(
        """
        CREATE TABLE jobs (
            company TEXT,
            title TEXT,
            url TEXT,
            canonical_url TEXT,
            first_seen TEXT
        )
        """
    )
    connection.execute(
        "INSERT INTO jobs VALUES (?, ?, ?, ?, ?)",
        (
            "Acme",
            "iOS Engineer",
            "https://example.com/jobs/9/?utm_source=a",
            "https://example.com/jobs/9",
            "2026-01-01T00:00:00+00:00",
        ),
    )
    connection.commit()
    connection.close()

    seen: dict = {}
    added = migrate_from_sqlite(db_path, seen)

    assert added == 1
    assert "https://example.com/jobs/9" in seen
    assert seen["https://example.com/jobs/9"]["title"] == "iOS Engineer"
