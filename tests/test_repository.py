from __future__ import annotations

from ai.models import JobAnalysisOutput, JobAnalysisRecord, PROMPT_VERSION
from tests.conftest import make_job_record, make_vacancy

NOW = "2026-07-02T10:00:00+00:00"


def _sample_analysis(job_id: str) -> JobAnalysisRecord:
    output = JobAnalysisOutput.model_validate(
        {
            "fit_score": 80,
            "apply_priority": "high",
            "confidence": "high",
            "seniority_match": "strong",
            "role_type": "platform",
            "domain_match": "strong",
            "architecture_match": "medium",
            "employment_type": "remote",
            "location_compatibility": "compatible",
            "language_risk": "none",
            "strong_matches": ["SDK"],
            "must_have_gaps": [],
            "nice_to_have_gaps": [],
            "risk_factors": [],
            "recommended_resume": "sdk",
            "referenced_fact_ids": ["pasha_premium_sdk"],
            "reason": "Good fit.",
        }
    )
    return JobAnalysisRecord(
        job_id=job_id,
        output=output,
        prefilter_score=70,
        job_content_hash="hash-job",
        candidate_profile_hash="hash-profile",
        prompt_version=PROMPT_VERSION,
        provider="fake",
        model="fake-model",
        analyzed_at=NOW,
    )


def test_save_and_get_cached_job_analysis(repo) -> None:
    job = make_job_record(make_vacancy(), now=NOW)
    repo.upsert_job(job)
    record = _sample_analysis(job.id)

    saved = repo.save_job_analysis(record)

    assert saved.id is not None
    cached = repo.get_cached_job_analysis(
        job_id=job.id,
        job_content_hash=record.job_content_hash,
        candidate_profile_hash=record.candidate_profile_hash,
        prompt_version=PROMPT_VERSION,
        model="fake-model",
    )

    assert cached is not None
    assert cached.id == saved.id
    assert cached.output.fit_score == 80
    assert cached.output.recommended_resume == "sdk"


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


def test_get_job_by_company_title_matches_normalized_role(repo) -> None:
    stored = make_job_record(
        make_vacancy(
            company="N-iX",
            title="Lead iOS Engineer (#5458)",
            url="https://careers.n-ix.com/jobs/4494044101-ios-leader/",
        ),
        now=NOW,
    )
    repo.upsert_job(stored)

    found = repo.get_job_by_company_title("N-iX", "Lead iOS Engineer")

    assert found is not None
    assert found.id == stored.id
