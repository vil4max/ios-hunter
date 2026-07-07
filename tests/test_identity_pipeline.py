from __future__ import annotations

from database.repository import utc_now
from parser.diff import compare_job
from tests.conftest import make_job_record, make_vacancy


def test_same_logical_vacancy_across_runs_is_not_new_twice(repo) -> None:
    first = make_vacancy(url="https://example.com/jobs/123?utm_source=a")
    now1 = "2026-07-02T10:00:00+00:00"
    record1, change1 = compare_job(None, first, now1)
    assert change1.change_type == "new"
    repo.upsert_job(record1)

    second = make_vacancy(url="https://example.com/jobs/123", title="Senior   iOS Developer")
    existing = repo.get_job_by_identity_key(second.identity_key)
    assert existing is not None
    now2 = "2026-07-02T12:00:00+00:00"
    _, change2 = compare_job(existing, second, now2)
    assert change2.change_type in {"unchanged", "updated"}


def test_updated_emitted_once_for_real_change(repo) -> None:
    vacancy = make_vacancy(url="https://example.com/jobs/123", description="Old")
    now1 = "2026-07-02T10:00:00+00:00"
    record1, _ = compare_job(None, vacancy, now1)
    repo.upsert_job(record1)

    incoming = make_vacancy(url="https://example.com/jobs/123", description="New")
    existing = repo.get_job_by_identity_key(incoming.identity_key)
    assert existing is not None
    now2 = "2026-07-02T12:00:00+00:00"
    record2, change2 = compare_job(existing, incoming, now2)
    assert change2.change_type == "updated"
    repo.upsert_job(record2)

    existing2 = repo.get_job_by_identity_key(incoming.identity_key)
    assert existing2 is not None
    now3 = "2026-07-02T13:00:00+00:00"
    _, change3 = compare_job(existing2, incoming, now3)
    assert change3.change_type == "unchanged"


def test_reopened_emitted_once(repo) -> None:
    vacancy = make_vacancy(url="https://example.com/jobs/123")
    now1 = "2026-07-02T10:00:00+00:00"
    record1, _ = compare_job(None, vacancy, now1)
    repo.upsert_job(record1)
    repo.mark_closed(record1.id, when="2026-07-02T11:00:00+00:00")

    incoming = make_vacancy(url="https://example.com/jobs/123")
    existing = repo.get_job_by_identity_key(incoming.identity_key)
    assert existing is not None
    now2 = "2026-07-02T12:00:00+00:00"
    record2, change2 = compare_job(existing, incoming, now2)
    assert change2.change_type == "reopened"
    repo.upsert_job(record2)

    existing2 = repo.get_job_by_identity_key(incoming.identity_key)
    assert existing2 is not None
    now3 = "2026-07-02T13:00:00+00:00"
    _, change3 = compare_job(existing2, incoming, now3)
    assert change3.change_type == "unchanged"

