from __future__ import annotations

import requests

from collector import company_watchlist
from collector.company_watchlist import collect_watchlist_company, extract_ios_jobs
from collector.types import STATUS_FAILED


def test_extract_ios_jobs_keeps_relevant_anchor_and_json_ld() -> None:
    html = """
    <a href="/jobs/senior-ios-engineer">Senior iOS Engineer</a>
    <a href="/jobs/backend-engineer">Backend Engineer</a>
    <article><a href="/jobs/mobile">Mobile Engineer</a><span>Native Swift and Kotlin</span></article>
    <script type="application/ld+json">
      {"@type":"JobPosting","title":"Swift Developer","url":"/vacancies/swift"}
    </script>
    """

    jobs, scanned = extract_ios_jobs("Acme", "https://acme.test/careers", html)

    assert {job["title"] for job in jobs} == {
        "Senior iOS Engineer",
        "Mobile Engineer",
        "Swift Developer",
    }
    assert scanned == 4


def test_extract_ios_jobs_rejects_marketing_page_without_job_url() -> None:
    html = '<a href="/services/ios-development">iOS Development Services</a>'

    jobs, scanned = extract_ios_jobs("Acme", "https://acme.test/careers", html)

    assert jobs == []
    assert scanned == 0


def test_unresolved_company_is_an_explicit_failed_source() -> None:
    result = collect_watchlist_company(
        {
            "name": "Acme",
            "slug": "acme",
            "company_site_url": "https://acme.test",
            "career_url": None,
        }
    )

    assert result.status == STATUS_FAILED
    assert result.source_id == "company-watchlist:acme"
    assert result.error == "official career URL unresolved"


def test_rate_limited_page_retries_with_impersonation(monkeypatch) -> None:
    response = requests.Response()
    response.status_code = 429
    error = requests.HTTPError(response=response)
    monkeypatch.setattr(company_watchlist, "fetch_text", lambda _url: (_ for _ in ()).throw(error))
    monkeypatch.setattr(
        company_watchlist,
        "fetch_impersonated",
        lambda _url: '<a href="/jobs/ios">iOS Engineer</a>',
    )

    result = collect_watchlist_company(
        {"name": "Acme", "slug": "acme", "career_url": "https://acme.test/careers"}
    )

    assert result.status == "healthy"
    assert [job["title"] for job in result.jobs] == ["iOS Engineer"]
