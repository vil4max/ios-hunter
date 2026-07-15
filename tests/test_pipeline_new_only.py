from __future__ import annotations

from integrations.notify import CollectReportStats
from parser.normalize import normalize_many
from scripts.run_pipeline import process_new_vacancies
from tests.conftest import make_vacancy


def test_second_identical_run_sends_zero_created(monkeypatch) -> None:
    alerts: list[int] = []

    def fake_hourly(sync_result, *, stats, board_url="", now=None):
        alerts.append(sync_result.created_count)

    monkeypatch.setattr("scripts.run_pipeline.notify_hourly_inbox", fake_hourly)
    monkeypatch.delenv("CAREER_AGENT_SYNC_ENABLED", raising=False)

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

    sent_count, marked, _ = process_new_vacancies(
        vacancies,
        seen,
        seed_only=False,
        duplicates_removed=2,
        failed_source_names=["DOU Top 50"],
    )
    assert sent_count == 1
    assert marked == 1
    assert alerts == [1]

    sent_count_2, marked_2, _ = process_new_vacancies(
        vacancies,
        seen,
        seed_only=False,
        duplicates_removed=2,
        failed_source_names=["DOU Top 50"],
    )
    assert sent_count_2 == 0
    assert marked_2 == 0
    assert alerts == [1, 0]


def test_seed_only_marks_without_sending(monkeypatch) -> None:
    calls: list[int] = []

    def fake_hourly(sync_result, *, stats, board_url="", now=None):
        calls.append(1)

    monkeypatch.setattr("scripts.run_pipeline.notify_hourly_inbox", fake_hourly)
    monkeypatch.delenv("CAREER_AGENT_SYNC_ENABLED", raising=False)

    vacancies = [make_vacancy(url="https://example.com/jobs/seed")]
    seen: dict = {}

    sent_count, marked, _ = process_new_vacancies(vacancies, seen, seed_only=True)
    assert sent_count == 0
    assert marked == 1
    assert calls == []
    assert "https://example.com/jobs/seed" in seen


def test_same_url_different_description_does_not_recount(monkeypatch) -> None:
    alerts: list[int] = []

    def fake_hourly(sync_result, *, stats, board_url="", now=None):
        alerts.append(sync_result.created_count)

    monkeypatch.setattr("scripts.run_pipeline.notify_hourly_inbox", fake_hourly)
    monkeypatch.delenv("CAREER_AGENT_SYNC_ENABLED", raising=False)

    first = [make_vacancy(url="https://example.com/jobs/2", description="Old")]
    second = [make_vacancy(url="https://example.com/jobs/2", description="Changed requirements")]
    seen: dict = {}

    process_new_vacancies(first, seen, seed_only=False)
    process_new_vacancies(second, seen, seed_only=False)

    assert alerts == [1, 0]


def test_multiple_new_vacancies_one_hourly_alert(monkeypatch) -> None:
    alerts: list[tuple[int, CollectReportStats]] = []

    def fake_hourly(sync_result, *, stats, board_url="", now=None):
        alerts.append((sync_result.created_count, stats))

    monkeypatch.setattr("scripts.run_pipeline.notify_hourly_inbox", fake_hourly)
    monkeypatch.delenv("CAREER_AGENT_SYNC_ENABLED", raising=False)

    vacancies = [
        make_vacancy(url="https://example.com/jobs/1", title="iOS Engineer"),
        make_vacancy(url="https://example.com/jobs/2", title="Swift Developer"),
    ]
    seen: dict = {}
    sent, marked, _ = process_new_vacancies(
        vacancies,
        seen,
        seed_only=False,
        duplicates_removed=3,
    )

    assert sent == 2
    assert marked == 2
    assert len(alerts) == 1
    assert alerts[0][0] == 2
    assert alerts[0][1] == CollectReportStats(
        found=2,
        seen_total=0,
        new_count=2,
        duplicates_removed=3,
        failed_source_names=(),
    )


def test_no_vacancies_still_sends_hourly_proof(monkeypatch) -> None:
    alerts: list[int] = []

    def fake_hourly(sync_result, *, stats, board_url="", now=None):
        alerts.append(sync_result.created_count)

    monkeypatch.setattr("scripts.run_pipeline.notify_hourly_inbox", fake_hourly)
    monkeypatch.delenv("CAREER_AGENT_SYNC_ENABLED", raising=False)

    sent, marked, _ = process_new_vacancies([], {}, seed_only=False)
    assert sent == 0
    assert marked == 0
    assert alerts == [0]
