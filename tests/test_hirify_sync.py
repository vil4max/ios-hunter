from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from openpyxl import Workbook

from config.settings import Settings
from integrations.hirify_export import (
    HirifyApplicationRow,
    map_hirify_stage,
    parse_applications_xlsx,
)
from planner.plan import ProjectCard
from project_sync.hirify_sync import (
    match_card,
    plan_row_transition,
    run_hirify_sync,
)
from reporter.hirify_sync import format_hirify_sync_message


def _settings() -> Settings:
    return Settings(
        github_token="token",
        github_repository="vil4max/ios-hunter",
        project_owner="vil4max",
        project_number=3,
        project_board_url="https://github.com/users/vil4max/projects/3",
        sync_enabled=True,
        seen_gate_enabled=False,
        stale_days=7,
        inbox_new_days=2,
        research_stale_days=5,
    )


def _card(
    *,
    item_id: str,
    company: str,
    title: str,
    status: str,
    url: str = "https://example.com/job",
) -> ProjectCard:
    now = datetime(2026, 7, 29, tzinfo=timezone.utc)
    return ProjectCard(
        item_id=item_id,
        issue_number=None,
        title=title,
        url=url,
        issue_url="",
        company=company,
        source="hirify.me",
        canonical_url=url,
        status=status,
        priority="",
        offer_probability="",
        follow_up=None,
        applied_at=None,
        created_at=now,
        updated_at=now,
        body="body",
    )


def _row(
    *,
    company: str = "ElevenLabs",
    title: str = "iOS Developer (AI)",
    stage: str = "Applied",
    job_url: str = "https://hirify.me/jobs/463438-ios-developer-ai",
    recruiter: str = "",
    updated_at: str = "2026-07-29 18:26:25",
) -> HirifyApplicationRow:
    return HirifyApplicationRow(
        job_title=title,
        job_url=job_url,
        company=company,
        date_applied=date(2026, 7, 29),
        stage=stage,
        feedback="",
        comment="",
        source="Hirify",
        recruiter_contact=recruiter,
        expected_salary="",
        work_type="remote",
        created_at=updated_at,
        updated_at=updated_at,
    )


def test_map_hirify_stage_matrix() -> None:
    assert map_hirify_stage("Applied").status == "Applied"
    assert map_hirify_stage("Viewed").status == "Applied"
    assert map_hirify_stage("No Response").status == "Applied"
    assert map_hirify_stage("HR Interview").status == "Screening"
    assert map_hirify_stage("Technical Interview").status == "Technical"
    assert map_hirify_stage("Test Task").status == "Technical"
    assert map_hirify_stage("Final Interview").status == "Post-Tech"
    offer = map_hirify_stage("Offer")
    assert offer.note_only is True
    assert offer.status is None
    rejected = map_hirify_stage("Rejected")
    assert rejected.status == "Archived"
    assert rejected.close_reason == "Rejected HR"


def test_parse_applications_xlsx(tmp_path: Path) -> None:
    path = tmp_path / "my_applications_2026-07-29.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(
        [
            "Job Title",
            "Job URL",
            "Company",
            "Date Applied",
            "Stage",
            "Feedback",
            "Comment",
            "Source",
            "Recruiter Contact",
            "Expected Salary",
            "Work Type",
            "Created At",
            "Updated At",
        ]
    )
    ws.append(
        [
            "iOS Developer (AI)",
            "https://hirify.me/jobs/463438-ios-developer-ai",
            "ElevenLabs",
            date(2026, 7, 29),
            "Applied",
            None,
            None,
            "Hirify",
            "https://elevenlabs.io/careers/job",
            None,
            "remote",
            "2026-07-29 18:26:25",
            "2026-07-29 18:26:25",
        ]
    )
    ws.append(
        [
            "iOS Developer (Swift/SwiftUI)",
            "https://hirify.me/jobs/781047-ios-developer-swiftswiftui",
            "частное лицо",
            date(2026, 7, 29),
            "Applied",
            None,
            None,
            "Hirify",
            "kcal_founder",
            None,
            "remote",
            "2026-07-29 18:14:55",
            "2026-07-29 18:14:55",
        ]
    )
    wb.save(path)

    rows = parse_applications_xlsx(path)
    assert len(rows) == 2
    assert rows[0].company == "ElevenLabs"
    assert rows[0].preferred_url.startswith("https://elevenlabs.io/")
    assert rows[1].recruiter_contact == "kcal_founder"
    assert "463438" in rows[0].fingerprint


def test_plan_row_transition_no_downgrade() -> None:
    technical = _card(
        item_id="1",
        company="ElevenLabs",
        title="iOS Developer",
        status="Technical",
    )
    action, status, _, _ = plan_row_transition(_row(stage="Applied"), technical)
    assert action == "noop"
    assert status == "Technical"

    applied = _card(
        item_id="2",
        company="ElevenLabs",
        title="iOS Developer",
        status="Applied",
    )
    action, status, _, _ = plan_row_transition(_row(stage="HR Interview"), applied)
    assert action == "update"
    assert status == "Screening"

    action, status, reason, closed = plan_row_transition(_row(stage="Rejected"), applied)
    assert action == "update"
    assert status == "Archived"
    assert reason == "Rejected HR"
    assert closed == "Applied"

    action, status, _, _ = plan_row_transition(_row(stage="Offer"), applied)
    assert action == "note"
    assert status == "Applied"

    action, status, _, _ = plan_row_transition(_row(stage="Applied"), None)
    assert action == "create"
    assert status == "Applied"


def test_match_card_prefers_url_then_title() -> None:
    cards = [
        _card(
            item_id="a",
            company="ElevenLabs",
            title="iOS Developer",
            status="Applied",
            url="https://jobs.ashbyhq.com/elevenlabs/abc",
        ),
        _card(
            item_id="b",
            company="ElevenLabs",
            title="Android Engineer",
            status="Applied",
            url="https://example.com/android",
        ),
    ]
    by_url = match_card(
        _row(
            job_url="https://jobs.ashbyhq.com/elevenlabs/abc",
            title="iOS Developer (AI)",
        ),
        cards,
    )
    assert by_url is not None
    assert by_url.item_id == "a"

    by_title = match_card(
        _row(
            job_url="https://hirify.me/jobs/other",
            title="iOS Developer (AI)",
            recruiter="",
        ),
        cards,
    )
    assert by_title is not None
    assert by_title.item_id == "a"


def test_run_hirify_sync_dry_run_and_seen(tmp_path: Path) -> None:
    settings = _settings()
    seen_path = tmp_path / "hirify_seen.json"
    cards = [
        _card(
            item_id="el",
            company="ElevenLabs",
            title="iOS Developer",
            status="Inbox",
            url="https://jobs.ashbyhq.com/elevenlabs/abc",
        )
    ]
    rows = [
        _row(
            stage="Applied",
            job_url="https://jobs.ashbyhq.com/elevenlabs/abc",
        ),
        _row(
            company="Karta.io",
            title="Founding Mobile Lead (Fintech)",
            stage="Applied",
            job_url="https://hirify.me/jobs/644315-founding-mobile-lead-fintech",
            updated_at="2026-07-29 17:00:00",
        ),
    ]

    result = run_hirify_sync(
        settings,
        dry_run=True,
        rows=rows,
        cards=cards,
        hirify_seen_path=seen_path,
        today=date(2026, 7, 29),
    )
    assert result.rows == 2
    assert result.skipped_seen == 0
    actions = {m.action for m in (result.mutations or [])}
    assert "would_update" in actions
    assert "would_create" in actions

    text = format_hirify_sync_message(result)
    assert text is not None
    assert "Hirify → CRM" in text

    first = run_hirify_sync(
        settings,
        dry_run=True,
        rows=rows[:1],
        cards=cards,
        hirify_seen_path=seen_path,
        today=date(2026, 7, 29),
    )
    assert len(first.mutations or []) == 1

    from database.hirify_seen import load_hirify_seen, mark_processed, save_hirify_seen

    seen = load_hirify_seen(seen_path)
    mark_processed(
        seen,
        rows[0].fingerprint,
        stage=rows[0].stage,
        company=rows[0].company,
        action="updated",
    )
    save_hirify_seen(seen_path, seen)

    second = run_hirify_sync(
        settings,
        dry_run=True,
        rows=rows[:1],
        cards=cards,
        hirify_seen_path=seen_path,
        today=date(2026, 7, 29),
    )
    assert second.skipped_seen == 1
    assert second.mutations == []


def test_sync_does_not_invent_missing_excel_rows(tmp_path: Path) -> None:
    settings = _settings()
    cards = [
        _card(
            item_id="k",
            company="Karta.io",
            title="Founding Mobile Lead (Fintech)",
            status="Applied",
            url="https://hirify.me/jobs/644315-founding-mobile-lead-fintech",
        )
    ]
    rows = [
        _row(
            company="ElevenLabs",
            title="iOS Developer (AI)",
            job_url="https://hirify.me/jobs/463438-ios-developer-ai",
        )
    ]
    result = run_hirify_sync(
        settings,
        dry_run=True,
        rows=rows,
        cards=cards,
        hirify_seen_path=tmp_path / "hirify_seen.json",
    )
    companies = {m.row.company for m in (result.mutations or [])}
    assert companies == {"ElevenLabs"}
    assert "Karta.io" not in companies
