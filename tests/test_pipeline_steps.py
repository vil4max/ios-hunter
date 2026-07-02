from __future__ import annotations

from apply.matcher import load_profile
from parser.activity import ActivitySummary
from parser.diff import JobChange
from parser.pipeline_steps import apply_job_change
from tests.conftest import make_job_record, make_vacancy

NOW = "2026-07-02T10:00:00+00:00"


def test_apply_job_change_records_new_activity(repo, monkeypatch) -> None:
    monkeypatch.setattr(
        "parser.pipeline_steps.process_actionable",
        lambda *args, **kwargs: False,
    )
    activity = ActivitySummary()
    vacancy = make_vacancy(title="Principal iOS Engineer")
    record = make_job_record(vacancy, now=NOW)
    repo.upsert_job(record)
    run_id = repo.start_run_metrics(NOW)
    change = JobChange(job_id=record.id, change_type="new")

    sent = apply_job_change(repo, run_id, record, change, {"match_threshold": 60}, NOW, activity)

    assert sent is False
    assert activity.new == 1
    assert activity.actionable == 1
    history = repo._conn.execute(
        "SELECT change_type FROM history WHERE job_id = ?",
        (record.id,),
    ).fetchone()
    assert history["change_type"] == "created"


def test_apply_job_change_records_updated_activity(repo, monkeypatch) -> None:
    monkeypatch.setattr(
        "parser.pipeline_steps.process_actionable",
        lambda *args, **kwargs: True,
    )
    activity = ActivitySummary()
    vacancy = make_vacancy(description="Updated SwiftUI requirements")
    record = make_job_record(vacancy, now=NOW)
    repo.upsert_job(record)
    run_id = repo.start_run_metrics(NOW)
    change = JobChange(
        job_id=record.id,
        change_type="updated",
        old_description="Old description",
        new_description=vacancy.description,
        diff="+ SwiftUI",
        change_summary="SwiftUI",
    )

    sent = apply_job_change(repo, run_id, record, change, load_profile(), NOW, activity)

    assert sent is True
    assert activity.updated == 1
    run_row = repo._conn.execute(
        "SELECT activity_type, change_summary FROM run_activity WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    assert run_row["activity_type"] == "updated"
    assert run_row["change_summary"] == "SwiftUI"
