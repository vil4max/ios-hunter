from __future__ import annotations

from pathlib import Path

from database.email_seen import (
    is_processed,
    load_email_seen,
    mark_processed,
    save_email_seen,
)


def test_email_seen_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "email_seen.json"
    seen = load_email_seen(path)
    assert seen == {}
    assert mark_processed(seen, "<id1>", kind="application_ack", company="Welltech")
    assert is_processed(seen, "<id1>")
    assert not mark_processed(seen, "<id1>", kind="application_ack")
    save_email_seen(path, seen)
    loaded = load_email_seen(path)
    assert "<id1>" in loaded
    assert loaded["<id1>"]["kind"] == "application_ack"
