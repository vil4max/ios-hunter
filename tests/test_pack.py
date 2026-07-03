from __future__ import annotations

from apply.cover_letter import render_cover_letter
from apply.matcher import MatchResult, load_profile
from apply.pack import (
    activity_emoji,
    build_application_pack,
    format_pack_message,
    process_actionable,
)
from apply import pack as pack_module
from apply.resume_picker import portfolio_url, resume_url
from tests.conftest import make_job_record, make_vacancy

NOW = "2026-07-02T10:00:00+00:00"


def _high_match() -> MatchResult:
    return MatchResult(
        score=85,
        strong=["SwiftUI", "UIKit", "Concurrency"],
        missing=[],
        remote_ok=True,
        resume_version="product",
    )


def test_activity_emoji_maps_known_types() -> None:
    assert activity_emoji("new") == "🟢 New"
    assert activity_emoji("updated") == "✏️ Updated"
    assert activity_emoji("reopened") == "🔄 Reopened"
    assert activity_emoji("other") == "📌"


def test_format_pack_message_includes_job_details() -> None:
    job = make_job_record(make_vacancy())
    match = _high_match()
    cover_letter = "Hello from the test suite."

    message = format_pack_message(job, "new", match, cover_letter)

    assert "🟢 New — Acme — Senior iOS Developer" in message
    assert "Match: 85%" in message
    assert "Strong: SwiftUI, UIKit, Concurrency" in message
    assert "Gap: —" in message
    assert "Cover letter:\nHello from the test suite." in message
    profile = load_profile()
    assert f"CV: {profile['cv_urls']['product']}" in message
    assert f"Portfolio: {profile['portfolio_url']}" in message
    assert f"Apply: {job.url}" in message


def test_format_pack_message_warns_on_remote_mismatch() -> None:
    job = make_job_record(make_vacancy(remote="onsite"))
    match = MatchResult(
        score=70,
        strong=["SwiftUI"],
        missing=[],
        remote_ok=False,
        resume_version="product",
    )

    message = format_pack_message(job, "new", match, "Letter")

    assert "⚠️ Remote preference mismatch" in message


def test_format_pack_message_adds_reopened_note() -> None:
    job = make_job_record(make_vacancy())
    message = format_pack_message(job, "reopened", _high_match(), "Letter")

    assert "🔄 Hiring likely restarted — worth reapplying" in message


def test_render_cover_letter_uses_profile_and_match(sample_profile) -> None:
    job = make_job_record(make_vacancy())
    match = MatchResult(
        score=80,
        strong=["SwiftUI", "UIKit"],
        missing=[],
        remote_ok=True,
        resume_version="ai",
    )

    letter = render_cover_letter(job, match, profile=sample_profile)

    assert "Max Vilchevskiy" in letter
    assert "Senior iOS Developer" in letter
    assert "Acme" in letter
    assert "voice AI on Apple Watch" in letter
    assert "SwiftUI" in letter


def test_resume_and_portfolio_urls_use_profile(sample_profile) -> None:
    match = MatchResult(
        score=80,
        strong=["AI"],
        missing=[],
        remote_ok=True,
        resume_version="ai",
    )

    assert resume_url(match, profile=sample_profile) == sample_profile["cv_urls"]["ai"]
    assert portfolio_url(profile=sample_profile) == sample_profile["portfolio_url"]


def test_build_application_pack_returns_match_and_letter() -> None:
    job = make_job_record(
        make_vacancy(description="SwiftUI, UIKit, async/await, and AI experience required")
    )

    match, letter = build_application_pack(job, "new")

    assert match.score >= 60
    assert "Max Vilchevskiy" in letter
    assert job.company in letter


def test_process_actionable_skips_below_threshold(repo, monkeypatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr(pack_module, "send_message", lambda text: sent.append(text))
    monkeypatch.setattr(
        pack_module,
        "build_application_pack",
        lambda job, activity_type: (
            MatchResult(score=50, strong=[], missing=[], remote_ok=True, resume_version="product"),
            "Low match letter",
        ),
    )

    job = make_job_record(make_vacancy())
    repo.upsert_job(job)

    sent_pack = process_actionable(repo, job, "new", {"match_threshold": 60}, NOW)

    assert sent_pack is False
    assert sent == []
    row = repo._conn.execute("SELECT COUNT(*) AS count FROM application_packs").fetchone()
    assert row["count"] == 0


def test_process_actionable_sends_and_persists_pack(repo, monkeypatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr(pack_module, "send_message", lambda text: sent.append(text))
    monkeypatch.setattr(
        pack_module,
        "build_application_pack",
        lambda job, activity_type: (_high_match(), "Strong match letter"),
    )

    job = make_job_record(make_vacancy())
    repo.upsert_job(job)

    sent_pack = process_actionable(
        repo,
        job,
        "updated",
        {"match_threshold": 60, "telegram": {"enabled": True}},
        NOW,
    )

    assert sent_pack is True
    assert len(sent) == 1
    assert "✏️ Updated — Acme — Senior iOS Developer" in sent[0]

    row = repo._conn.execute(
        "SELECT activity_type, match_score, cover_letter, notified_at FROM application_packs WHERE job_id = ?",
        (job.id,),
    ).fetchone()

    assert row["activity_type"] == "updated"
    assert row["match_score"] == 85
    assert row["cover_letter"] == "Strong match letter"
    assert row["notified_at"] is not None


def test_process_actionable_respects_disabled_telegram(repo, monkeypatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr(pack_module, "send_message", lambda text: sent.append(text))
    monkeypatch.setattr(
        pack_module,
        "build_application_pack",
        lambda job, activity_type: (_high_match(), "Strong match letter"),
    )

    job = make_job_record(make_vacancy())
    repo.upsert_job(job)

    sent_pack = process_actionable(
        repo,
        job,
        "new",
        {"match_threshold": 60, "telegram": {"enabled": False}},
        NOW,
    )

    assert sent_pack is True
    assert sent == []

    row = repo._conn.execute("SELECT COUNT(*) AS count FROM application_packs").fetchone()
    assert row["count"] == 1


def test_process_actionable_skips_when_role_already_notified(repo, monkeypatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr(pack_module, "send_message", lambda text: sent.append(text))
    monkeypatch.setattr(
        pack_module,
        "build_application_pack",
        lambda job, activity_type: (_high_match(), "Strong match letter"),
    )

    first = make_job_record(
        make_vacancy(
            company="N-iX",
            title="Lead iOS Engineer (#5458)",
            url="https://careers.n-ix.com/jobs/4494044101-ios-leader/",
        )
    )
    repo.upsert_job(first)
    process_actionable(
        repo,
        first,
        "new",
        {"match_threshold": 60, "telegram": {"enabled": True}},
        NOW,
    )

    second = make_job_record(
        make_vacancy(
            company="N-iX",
            title="Lead iOS Engineer",
            url="https://careers.n-ix.com/jobs/4912838101?gh_jid=4912838101",
        )
    )
    repo.upsert_job(second)

    sent_pack = process_actionable(
        repo,
        second,
        "new",
        {"match_threshold": 60, "telegram": {"enabled": True}},
        NOW,
    )

    assert sent_pack is False
    assert len(sent) == 1
