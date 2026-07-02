from __future__ import annotations

from tests.conftest import make_job_record, make_vacancy

NOW = "2026-07-02T10:00:00+00:00"


def test_upsert_and_fetch_job_by_hash(repo) -> None:
    vacancy = make_vacancy()
    job = make_job_record(vacancy, now=NOW)
    repo.upsert_job(job)

    stored = repo.get_job_by_hash(vacancy.hash)

    assert stored is not None
    assert stored.title == vacancy.title
    assert stored.company == vacancy.company
    assert stored.status == "open"


def test_mark_closed_updates_status_and_counts(repo) -> None:
    open_job = make_job_record(
        make_vacancy(title="Senior iOS Developer", url="https://example.com/open"),
        now=NOW,
    )
    closed_job = make_job_record(
        make_vacancy(title="Staff iOS Engineer", url="https://example.com/closed"),
        now=NOW,
    )
    repo.upsert_job(open_job)
    repo.upsert_job(closed_job)
    repo.mark_closed(closed_job.id, NOW)

    stored = repo.get_job_by_id(closed_job.id)

    assert stored is not None
    assert stored.status == "closed"
    assert stored.description is None
    assert repo.count_open_jobs() == 1
    assert repo.count_tracked_jobs() == 2


def test_upsert_source_health_tracks_consecutive_failures(repo) -> None:
    repo.upsert_source_health(
        source_id="alpha",
        source_name="Alpha",
        source_url="https://alpha.example",
        status="failed",
        error="timeout",
        response_ms=1000,
        jobs_count=0,
    )
    repo.upsert_source_health(
        source_id="alpha",
        source_name="Alpha",
        source_url="https://alpha.example",
        status="failed",
        error="timeout",
        response_ms=900,
        jobs_count=0,
    )

    row = repo._conn.execute(
        "SELECT consecutive_failures, status FROM source_health WHERE source_id = ?",
        ("alpha",),
    ).fetchone()

    assert row["status"] == "failed"
    assert row["consecutive_failures"] == 2

    repo.upsert_source_health(
        source_id="alpha",
        source_name="Alpha",
        source_url="https://alpha.example",
        status="healthy",
        error=None,
        response_ms=200,
        jobs_count=3,
    )

    row = repo._conn.execute(
        "SELECT consecutive_failures, status FROM source_health WHERE source_id = ?",
        ("alpha",),
    ).fetchone()

    assert row["status"] == "healthy"
    assert row["consecutive_failures"] == 0


def test_prune_jobs_older_than_removes_stale_jobs(repo) -> None:
    stale = make_job_record(
        make_vacancy(title="Legacy iOS Role", url="https://example.com/stale"),
        now="2026-01-01 00:00:00",
        last_seen="2026-01-01 00:00:00",
    )
    fresh = make_job_record(
        make_vacancy(title="Current iOS Role", url="https://example.com/fresh"),
        now=NOW,
    )
    repo.upsert_job(stale)
    repo.upsert_job(fresh)

    removed = repo.prune_jobs_older_than(days=45)

    assert removed == 1
    assert repo.get_job_by_id(stale.id) is None
    assert repo.get_job_by_id(fresh.id) is not None
