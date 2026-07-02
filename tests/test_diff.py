from __future__ import annotations

from parser.diff import compare_job, line_diff, summarize_diff
from tests.conftest import make_job_record, make_vacancy

NOW = "2026-07-02T10:00:00+00:00"


def test_compare_job_detects_new_vacancy() -> None:
    vacancy = make_vacancy()

    record, change = compare_job(None, vacancy, NOW)

    assert change.change_type == "new"
    assert record.id == vacancy.hash
    assert record.status == "open"


def test_compare_job_detects_reopened_vacancy() -> None:
    vacancy = make_vacancy()
    existing = make_job_record(vacancy, status="closed", description=None)

    record, change = compare_job(existing, vacancy, NOW)

    assert change.change_type == "reopened"
    assert record.status == "open"
    assert record.first_seen == existing.first_seen


def test_compare_job_detects_unchanged_vacancy() -> None:
    vacancy = make_vacancy()
    existing = make_job_record(vacancy)

    _, change = compare_job(existing, vacancy, NOW)

    assert change.change_type == "unchanged"
    assert change.change_summary is None


def test_compare_job_detects_description_update() -> None:
    vacancy = make_vacancy(description="SwiftUI, UIKit, and Combine required")
    existing = make_job_record(vacancy, description="SwiftUI and UIKit experience required")

    record, change = compare_job(existing, vacancy, NOW)

    assert change.change_type == "updated"
    assert change.diff
    assert change.old_description == existing.description
    assert change.new_description == vacancy.description
    assert record.description == vacancy.description


def test_compare_job_detects_title_update() -> None:
    incoming = make_vacancy(title="Lead iOS Engineer")
    existing = make_job_record(
        make_vacancy(title="Senior iOS Developer"),
        id=incoming.hash,
    )

    _, change = compare_job(existing, incoming, NOW)

    assert change.change_type == "updated"
    assert "title: Lead iOS Engineer" in (change.diff or "")


def test_line_diff_formats_added_and_removed_lines() -> None:
    diff = line_diff("old line", "new line")

    assert "- old line" in diff
    assert "+ new line" in diff


def test_summarize_diff_returns_added_preview() -> None:
    diff = "+ SwiftUI required\n+ UIKit required\n- Objective-C"

    summary = summarize_diff(diff)

    assert "SwiftUI required" in summary
    assert "UIKit required" in summary
