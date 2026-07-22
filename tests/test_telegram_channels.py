from __future__ import annotations

from collector.telegram_channels import (
    extract_title,
    is_candidate_post,
    job_from_message,
    looks_like_vacancy,
    should_keep_message,
)


VACANCY_IOS = """
#ios #swift #вакансія
Senior iOS Engineer
SmartTek Solutions
Swift, UIKit, 5+ years
За деталями пишіть - @recruiter
""".strip()

CANDIDATE_IOS = """
#ios #candidates
Senior iOS Developer looking for new opportunities
Location: Kyiv
English: B2
CV: https://drive.google.com/file/d/xyz
""".strip()

BACKEND_VACANCY = """
#python #вакансія
Senior Backend Engineer
Python, TypeScript
""".strip()


def test_extract_title_skips_hashtag_only_line() -> None:
    assert extract_title(VACANCY_IOS) == "Senior iOS Engineer"


def test_is_candidate_post_detects_seeking() -> None:
    assert is_candidate_post(CANDIDATE_IOS) is True
    assert is_candidate_post(VACANCY_IOS) is False


def test_looks_like_vacancy() -> None:
    assert looks_like_vacancy(VACANCY_IOS) is True
    assert looks_like_vacancy(BACKEND_VACANCY) is True


def test_should_keep_only_ios_vacancies() -> None:
    assert should_keep_message(VACANCY_IOS) is True
    assert should_keep_message(CANDIDATE_IOS) is False
    assert should_keep_message(BACKEND_VACANCY) is False


def test_job_from_message_builds_telegram_url() -> None:
    job = job_from_message("itrecruit_ua", 12345, VACANCY_IOS)
    assert job is not None
    assert job["title"] == "Senior iOS Engineer"
    assert job["url"] == "https://t.me/itrecruit_ua/12345"
    assert job["source"] == "telegram"
    assert job["source_job_id"] == "itrecruit_ua:12345"
    assert job["company"] == "Telegram @itrecruit_ua"


def test_job_from_message_drops_candidates() -> None:
    assert job_from_message("itrecruit_ua", 1, CANDIDATE_IOS) is None
