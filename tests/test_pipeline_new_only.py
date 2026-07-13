from __future__ import annotations

from pathlib import Path

from database.seen import load_seen, save_seen
from integrations.notify import CollectReportStats
from parser.normalize import normalize_many
from scripts.run_pipeline import process_new_vacancies
from tests.conftest import make_vacancy


def test_second_identical_run_sends_empty_report(tmp_path: Path, monkeypatch) -> None:
    batches: list[list[str]] = []
    empty_reports: list[CollectReportStats] = []

    def fake_notify(vacancies, *, now=None, stats=None):
        batches.append([v.url for v in vacancies])
        return len(vacancies)

    def fake_empty(*, stats: CollectReportStats, now=None):
        empty_reports.append(stats)

    monkeypatch.setattr("scripts.run_pipeline.notify_new_vacancies", fake_notify)
    monkeypatch.setattr("scripts.run_pipeline.notify_empty_report", fake_empty)

    vacancies = normalize_many(
        [
            {
                "company": "Acme",
                "title": "Senior iOS Engineer",
                "url": "https://example.com/jobs/1",
                "source": "test",
            }
        ]
    )
    seen: dict = {}

    sent_count, marked = process_new_vacancies(
        vacancies,
        seen,
        seed_only=False,
        duplicates_removed=2,
        failed_source_names=["DOU Top 50"],
    )
    assert sent_count == 1
    assert marked == 1
    assert batches == [["https://example.com/jobs/1"]]
    assert empty_reports == []

    sent_count_2, marked_2 = process_new_vacancies(
        vacancies,
        seen,
        seed_only=False,
        duplicates_removed=2,
        failed_source_names=["DOU Top 50"],
    )
    assert sent_count_2 == 0
    assert marked_2 == 0
    assert len(batches) == 1
    assert empty_reports == [
        CollectReportStats(
            found=1,
            seen_total=1,
            new_count=0,
            duplicates_removed=2,
            failed_source_names=("DOU Top 50",),
        )
    ]


def test_seed_only_marks_without_sending(monkeypatch) -> None:
    batches: list[list[str]] = []
    empty_reports: list[CollectReportStats] = []

    def fake_notify(vacancies, *, now=None, stats=None):
        batches.append([v.url for v in vacancies])
        return len(vacancies)

    def fake_empty(*, stats: CollectReportStats, now=None):
        empty_reports.append(stats)

    monkeypatch.setattr("scripts.run_pipeline.notify_new_vacancies", fake_notify)
    monkeypatch.setattr("scripts.run_pipeline.notify_empty_report", fake_empty)

    vacancies = [make_vacancy(url="https://example.com/jobs/seed")]
    seen: dict = {}

    sent_count, marked = process_new_vacancies(vacancies, seen, seed_only=True)
    assert sent_count == 0
    assert marked == 1
    assert batches == []
    assert empty_reports == []
    assert "https://example.com/jobs/seed" in seen


def test_same_url_different_description_does_not_resend(monkeypatch) -> None:
    batches: list[list[str]] = []
    empty_reports: list[CollectReportStats] = []

    def fake_notify(vacancies, *, now=None, stats=None):
        batches.append([v.url for v in vacancies])
        return len(vacancies)

    def fake_empty(*, stats: CollectReportStats, now=None):
        empty_reports.append(stats)

    monkeypatch.setattr("scripts.run_pipeline.notify_new_vacancies", fake_notify)
    monkeypatch.setattr("scripts.run_pipeline.notify_empty_report", fake_empty)

    first = [make_vacancy(url="https://example.com/jobs/2", description="Old")]
    second = [make_vacancy(url="https://example.com/jobs/2", description="Changed requirements")]
    seen: dict = {}

    process_new_vacancies(first, seen, seed_only=False)
    process_new_vacancies(second, seen, seed_only=False)

    assert len(batches) == 1
    assert len(empty_reports) == 1
    assert empty_reports[0].new_count == 0
    assert empty_reports[0].found == 1


def test_new_urls_sent_in_one_batch(tmp_path: Path, monkeypatch) -> None:
    batches: list[list[str]] = []

    def fake_notify(vacancies, *, now=None, stats=None):
        batches.append([v.url for v in vacancies])
        return len(vacancies)

    monkeypatch.setattr("scripts.run_pipeline.notify_new_vacancies", fake_notify)
    path = tmp_path / "seen.json"
    seen = load_seen(path)

    first = [make_vacancy(url="https://example.com/jobs/a")]
    second = [
        make_vacancy(url="https://example.com/jobs/a"),
        make_vacancy(url="https://example.com/jobs/b", title="iOS Engineer II"),
    ]

    process_new_vacancies(first, seen, seed_only=False)
    save_seen(path, seen)
    seen = load_seen(path)
    process_new_vacancies(second, seen, seed_only=False)

    assert batches == [
        ["https://example.com/jobs/a"],
        ["https://example.com/jobs/b"],
    ]


def test_multiple_new_vacancies_one_telegram_call(monkeypatch) -> None:
    batches: list[list[str]] = []
    notify_stats: list[CollectReportStats] = []

    def fake_notify(vacancies, *, now=None, stats=None):
        batches.append([v.url for v in vacancies])
        if stats is not None:
            notify_stats.append(stats)
        return len(vacancies)

    monkeypatch.setattr("scripts.run_pipeline.notify_new_vacancies", fake_notify)

    vacancies = [
        make_vacancy(url="https://example.com/jobs/1", title="iOS Engineer"),
        make_vacancy(url="https://example.com/jobs/2", title="Swift Developer"),
    ]
    seen: dict = {}
    sent, marked = process_new_vacancies(
        vacancies,
        seen,
        seed_only=False,
        duplicates_removed=3,
    )

    assert sent == 2
    assert marked == 2
    assert batches == [
        ["https://example.com/jobs/1", "https://example.com/jobs/2"],
    ]
    assert notify_stats == [
        CollectReportStats(
            found=2,
            seen_total=0,
            new_count=2,
            duplicates_removed=3,
            failed_source_names=(),
        )
    ]


def test_no_vacancies_sends_empty_report(monkeypatch) -> None:
    empty_reports: list[CollectReportStats] = []

    def fake_empty(*, stats: CollectReportStats, now=None):
        empty_reports.append(stats)

    monkeypatch.setattr("scripts.run_pipeline.notify_empty_report", fake_empty)

    sent, marked = process_new_vacancies([], {}, seed_only=False)
    assert sent == 0
    assert marked == 0
    assert empty_reports == [
        CollectReportStats(
            found=0,
            seen_total=0,
            new_count=0,
            duplicates_removed=0,
            failed_source_names=(),
        )
    ]
