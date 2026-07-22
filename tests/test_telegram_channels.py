from __future__ import annotations

from datetime import datetime, timezone

from collector.telegram_channels import (
    extract_company,
    extract_title,
    is_candidate_post,
    job_from_message,
    looks_like_vacancy,
    should_keep_message,
)
from parser.normalize import is_ios_job


VACANCY_IOS = """
#ios #swift #вакансія
Senior iOS Engineer
SmartTek Solutions шукає Senior iOS Engineer
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

STUDIOS_SEO = """
⚓️Admiral Studios шукає SEO Specialist
#вакансія #seo
""".strip()

QA_CRYPTO = """
🚀 We’re Hiring: Manual QA Engineer (Crypto Casino | AI-Native Team)
#вакансія #qa
""".strip()

GREETING = """
Всім хай 🙋🏻‍♀️
""".strip()

PARTNERSHIP = """
We propose partnership on the development of White-Label, Outsourcing & Outstaffing projects.
""".strip()

REMOTEJOBSS_IOS = """
💼 JOB OPPORTUNITY
🚀 Senior iOS Engineer
🏢 Company: Acme Labs
━━━━━━━━━━━━━━━
✅ Tags
#mobile#engineering#remote
━━━━━━━━━━━━━━━
Ready to Apply?
👇 Apply using the button below
""".strip()

ITFREELANCERS_IOS = """
‼️‼️🆕 We're looking for a Senior Swift / iOS Engineer for a remote product team.
Tech: Swift, UIKit, SwiftUI
#ITJobs#iOS#Swift
Send your resume to jobs@example.com
‼️‼️
""".strip()

ITFREELANCERS_QA = """
‼️‼️🆕 QA Engineer / Software Tester (Freelance / Remote)
We're looking for a detail-oriented QA Engineer.
#ITJobs#QA
‼️‼️
""".strip()


def test_is_ios_job_rejects_studios_substring() -> None:
    assert not is_ios_job(STUDIOS_SEO)
    assert not is_ios_job("Mind Studios Designer")


def test_extract_title_skips_hashtag_only_line() -> None:
    assert extract_title(VACANCY_IOS) == "Senior iOS Engineer"


def test_extract_company_from_hiring_line() -> None:
    assert extract_company(VACANCY_IOS) == "SmartTek Solutions"


def test_is_candidate_post_detects_seeking() -> None:
    assert is_candidate_post(CANDIDATE_IOS) is True
    assert is_candidate_post(VACANCY_IOS) is False


def test_looks_like_vacancy() -> None:
    assert looks_like_vacancy(VACANCY_IOS) is True
    assert looks_like_vacancy(GREETING) is False


def test_should_keep_only_ios_hiring_posts() -> None:
    assert should_keep_message(VACANCY_IOS) is True
    assert should_keep_message(CANDIDATE_IOS) is False
    assert should_keep_message(BACKEND_VACANCY) is False
    assert should_keep_message(STUDIOS_SEO) is False
    assert should_keep_message(QA_CRYPTO) is False
    assert should_keep_message(GREETING) is False
    assert should_keep_message(PARTNERSHIP) is False
    assert should_keep_message(REMOTEJOBSS_IOS) is True
    assert should_keep_message(ITFREELANCERS_IOS) is True
    assert should_keep_message(ITFREELANCERS_QA) is False


def test_remotejobss_parses_role_and_company() -> None:
    job = job_from_message("remotejobss", 99, REMOTEJOBSS_IOS)
    assert job is not None
    assert job["title"] == "Senior iOS Engineer"
    assert job["company"] == "Acme Labs"
    assert "Ready to Apply" in job["description"]


def test_itfreelancers_keeps_english_ios_hiring() -> None:
    job = job_from_message("itfreelancers", 50, ITFREELANCERS_IOS)
    assert job is not None
    assert "Swift" in job["title"] or "iOS" in job["title"]
    assert job_from_message("itfreelancers", 51, ITFREELANCERS_QA) is None


def test_job_from_message_builds_telegram_url_and_date() -> None:
    published = datetime(2026, 7, 22, 10, 0, tzinfo=timezone.utc)
    job = job_from_message("itrecruit_ua", 12345, VACANCY_IOS, published_at=published)
    assert job is not None
    assert job["title"] == "Senior iOS Engineer"
    assert job["company"] == "SmartTek Solutions"
    assert job["url"] == "https://t.me/itrecruit_ua/12345"
    assert job["source"] == "telegram"
    assert job["source_job_id"] == "itrecruit_ua:12345"
    assert job["published_at"] == published.isoformat()
    assert "UIKit" in job["description"]


def test_job_from_message_drops_junk() -> None:
    assert job_from_message("itrecruit_ua", 1, CANDIDATE_IOS) is None
    assert job_from_message("itrecruit_ua", 2, STUDIOS_SEO) is None
    assert job_from_message("itrecruit_ua", 3, QA_CRYPTO) is None
    assert job_from_message("itrecruit_ua", 4, GREETING) is None
