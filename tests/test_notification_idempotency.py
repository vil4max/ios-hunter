from __future__ import annotations

from apply.pack import save_pack
from tests.conftest import make_job_record, make_vacancy


def test_same_notification_event_cannot_be_sent_twice(repo, monkeypatch, sample_profile) -> None:
    sent: list[str] = []

    def fake_send_message(text: str) -> None:
        sent.append(text)

    monkeypatch.setattr("apply.pack.send_message", fake_send_message)

    vacancy = make_vacancy(url="https://example.com/jobs/123")
    job = make_job_record(vacancy)
    repo.upsert_job(job)

    message = "Test message"
    detected_at = "2026-07-02T10:00:00+00:00"

    ok1 = save_pack(
        repo,
        job,
        "new",
        detected_at,
        message,
        sample_profile,
        match_score=80,
        match_strong=["SwiftUI"],
        match_missing=[],
        resume_version="default",
        cover_letter="",
    )
    ok2 = save_pack(
        repo,
        job,
        "new",
        detected_at,
        message,
        sample_profile,
        match_score=80,
        match_strong=["SwiftUI"],
        match_missing=[],
        resume_version="default",
        cover_letter="",
    )

    assert ok1 is True
    assert ok2 is True
    assert len(sent) == 1


def test_failed_send_can_retry_after_lock_ttl(repo, monkeypatch, sample_profile) -> None:
    calls = 0

    def flaky_send_message(_: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("network down")

    monkeypatch.setattr("apply.pack.send_message", flaky_send_message)
    t1 = "2026-07-02T10:00:00+00:00"
    monkeypatch.setattr("apply.pack.utc_now", lambda: t1)

    vacancy = make_vacancy(url="https://example.com/jobs/123")
    job = make_job_record(vacancy)
    repo.upsert_job(job)

    message = "Test message"
    detected_at = t1

    try:
        save_pack(
            repo,
            job,
            "new",
            detected_at,
            message,
            sample_profile,
            match_score=80,
            match_strong=["SwiftUI"],
            match_missing=[],
            resume_version="default",
            cover_letter="",
        )
    except RuntimeError:
        pass

    assert calls == 1

    t2 = "2026-07-02T10:01:00+00:00"
    monkeypatch.setattr("apply.pack.utc_now", lambda: t2)
    ok2 = save_pack(
        repo,
        job,
        "new",
        detected_at,
        message,
        sample_profile,
        match_score=80,
        match_strong=["SwiftUI"],
        match_missing=[],
        resume_version="default",
        cover_letter="",
    )
    assert ok2 is True
    assert calls == 1

    t3 = "2026-07-02T10:11:00+00:00"
    monkeypatch.setattr("apply.pack.utc_now", lambda: t3)
    ok3 = save_pack(
        repo,
        job,
        "new",
        detected_at,
        message,
        sample_profile,
        match_score=80,
        match_strong=["SwiftUI"],
        match_missing=[],
        resume_version="default",
        cover_letter="",
    )
    assert ok3 is True
    assert calls == 2


