from __future__ import annotations

from pathlib import Path

import apply.pack as pack_module
from apply.matcher import MatchResult
from parser.normalize import normalize_many
from parser.pipeline_steps import send_company_watch_alerts
from scripts.run_pipeline import process_vacancies
from tests.conftest import sample_profile, sample_skills_map

NOW_1 = "2026-07-09T10:00:00+00:00"
NOW_2 = "2026-07-09T11:00:00+00:00"

SAMPLE_JOBS = [
    {
        "company": "Playtech",
        "title": "iOS Developer",
        "url": "https://jobs.dou.ua/companies/playtech/vacancies/361257/",
        "source": "dou",
        "source_job_id": "361257",
    },
    {
        "company": "Uklon",
        "title": "iOS Engineer Senior (Rider Team)",
        "url": "https://jobs.dou.ua/companies/uklon/vacancies/363708/",
        "source": "dou",
        "source_job_id": "363708",
    },
    {
        "company": "Uklon",
        "title": "iOS Engineer Senior (Finance Team)",
        "url": "https://jobs.dou.ua/companies/uklon/vacancies/357039/",
        "source": "dou",
        "source_job_id": "357039",
    },
    {
        "company": "Uklon",
        "title": "iOS Engineer",
        "url": "https://jobs.dou.ua/companies/uklon/vacancies/111111/",
        "source": "dou",
        "source_job_id": "111111",
    },
]


def _high_match() -> MatchResult:
    return MatchResult(
        score=85,
        strong=["SwiftUI", "UIKit"],
        missing=[],
        remote_ok=True,
        resume_version="product",
    )


def test_identical_second_run_produces_no_repeat_activity_or_alerts(
    repo,
    sample_profile,
    sample_skills_map,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TELEGRAM_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setattr("apply.matcher.match_job", lambda job, profile=None, skills_map=None: _high_match())
    monkeypatch.setattr("apply.intelligence.match_job", lambda job, profile=None, skills_map=None: _high_match())

    class DisabledAnalyzer:
        def enabled(self) -> bool:
            return False

    monkeypatch.setattr("apply.intelligence.JobAnalyzer", lambda base_dir=None: DisabledAnalyzer())

    sent: list[str] = []
    monkeypatch.setattr(pack_module, "send_message", lambda text: sent.append(text))
    monkeypatch.setattr("parser.pipeline_steps.send_message", lambda text: sent.append(text))

    run_id = repo.start_run_metrics(NOW_1)
    vacancies = normalize_many(SAMPLE_JOBS)

    activity_first, _, packs_first = process_vacancies(
        repo,
        run_id,
        vacancies,
        sample_profile,
        sample_skills_map,
        NOW_1,
    )
    company_watch_first = send_company_watch_alerts(repo, Path("/tmp"))
    first_sent_count = len(sent)

    assert activity_first.new > 0
    assert company_watch_first == 1
    assert first_sent_count > 0
    assert packs_first > 0

    activity_second, _, packs_second = process_vacancies(
        repo,
        run_id,
        vacancies,
        sample_profile,
        sample_skills_map,
        NOW_2,
    )
    company_watch_second = send_company_watch_alerts(repo, Path("/tmp"))

    assert activity_second.new == 0
    assert activity_second.updated == 0
    assert activity_second.reopened == 0
    assert packs_second == 0
    assert company_watch_second == 0
    assert len(sent) == first_sent_count


def test_second_run_skips_telegram_even_when_url_changes_for_same_role(
    repo,
    sample_profile,
    sample_skills_map,
    monkeypatch,
) -> None:
    sent: list[str] = []

    def capture_send(text: str) -> None:
        sent.append(text)

    monkeypatch.setenv("TELEGRAM_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setattr(pack_module, "send_message", capture_send)
    monkeypatch.setattr("apply.matcher.match_job", lambda job, profile=None, skills_map=None: _high_match())
    monkeypatch.setattr("apply.intelligence.match_job", lambda job, profile=None, skills_map=None: _high_match())

    class DisabledAnalyzer:
        def enabled(self) -> bool:
            return False

    monkeypatch.setattr("apply.intelligence.JobAnalyzer", lambda base_dir=None: DisabledAnalyzer())

    run_id = repo.start_run_metrics(NOW_1)
    first_batch = normalize_many([SAMPLE_JOBS[0]])
    activity_first, _, packs_first = process_vacancies(
        repo,
        run_id,
        first_batch,
        sample_profile,
        sample_skills_map,
        NOW_1,
    )
    assert activity_first.new == 1
    assert packs_first == 1
    assert len(sent) == 1

    sent.clear()
    second_batch = normalize_many(
        [
            {
                "company": "Playtech",
                "title": "iOS Developer",
                "url": "https://careers.playtech.com/jobs/999?gh_jid=999",
                "source": "company",
                "source_job_id": "999",
            }
        ]
    )
    activity_second, _, packs_second = process_vacancies(
        repo,
        run_id,
        second_batch,
        sample_profile,
        sample_skills_map,
        NOW_2,
    )

    assert activity_second.new == 0
    assert activity_second.updated == 0
    assert activity_second.reopened == 0
    assert packs_second == 0
    assert sent == []
