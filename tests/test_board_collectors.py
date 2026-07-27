from __future__ import annotations

import pytest

from collector import companies


@pytest.fixture
def stub_json(monkeypatch: pytest.MonkeyPatch):
    def apply(payloads):
        def fake_fetch(url: str, **_kwargs):
            if callable(payloads):
                return payloads(url)
            return payloads

        monkeypatch.setattr(companies, "fetch_json", fake_fetch)

    return apply


def test_teamtailor_follows_next_url(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        "https://jobs.acme.com/jobs.json": {
            "jobs": [
                {
                    "title": "Senior iOS Engineer",
                    "id": 1,
                    "links": {"careersite-job-url": "https://jobs.acme.com/jobs/1"},
                    "location": {"city": "Kyiv"},
                    "body": "Swift",
                },
                {"title": "Recruiter", "id": 2, "url": "https://jobs.acme.com/jobs/2"},
            ],
            "next_url": "https://jobs.acme.com/jobs.json?page=2",
        },
        "https://jobs.acme.com/jobs.json?page=2": {
            "jobs": [{"title": "Swift Developer", "id": 3, "url": "https://jobs.acme.com/jobs/3"}],
        },
    }
    monkeypatch.setattr(companies, "fetch_json", lambda url, **_k: pages[url])

    result = companies.collect_teamtailor("Acme", "https://jobs.acme.com/jobs.json")

    assert result.items_scanned == 3
    assert [job["url"] for job in result.jobs] == [
        "https://jobs.acme.com/jobs/1",
        "https://jobs.acme.com/jobs/3",
    ]
    assert result.jobs[0]["location"] == "Kyiv"


def test_teamtailor_stops_on_self_referencing_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_fetch(url: str, **_kwargs):
        calls.append(url)
        return {"jobs": [], "next_url": url}

    monkeypatch.setattr(companies, "fetch_json", fake_fetch)

    result = companies.collect_teamtailor("Acme", "https://jobs.acme.com/jobs.json")

    assert calls == ["https://jobs.acme.com/jobs.json"]
    assert result.status == "healthy"


def test_teamtailor_stops_at_page_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_fetch(url: str, **_kwargs):
        calls.append(url)
        return {"jobs": [], "next_url": f"https://jobs.acme.com/jobs.json?page={len(calls)}"}

    monkeypatch.setattr(companies, "fetch_json", fake_fetch)

    companies.collect_teamtailor("Acme", "https://jobs.acme.com/jobs.json")

    assert len(calls) == companies._MAX_FEED_PAGES


def test_teamtailor_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(companies, "fetch_json", lambda url, **_k: (_ for _ in ()).throw(OSError("down")))

    result = companies.collect_teamtailor("Acme", "https://jobs.acme.com/jobs.json")

    assert result.status == "failed"
    assert result.items_scanned == 0


def test_greenhouse_maps_fields(stub_json) -> None:
    stub_json(
        {
            "jobs": [
                {
                    "title": "iOS Engineer",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                    "id": 1,
                    "content": "Swift",
                    "location": {"name": "Kyiv, Ukraine"},
                    "updated_at": "2026-07-01",
                },
                {"title": "Data Analyst", "absolute_url": "https://boards.greenhouse.io/acme/jobs/2"},
            ]
        }
    )

    result = companies.collect_greenhouse("Acme", "acme")

    assert result.items_scanned == 2
    assert len(result.jobs) == 1
    assert result.jobs[0]["location"] == "Kyiv, Ukraine"
    assert result.jobs[0]["updated_at"] == "2026-07-01"


def test_greenhouse_accepts_plain_string_location(stub_json) -> None:
    stub_json({"jobs": [{"title": "iOS Engineer", "url": "https://x/1", "location": "Remote"}]})

    assert companies.collect_greenhouse("Acme", "acme").jobs[0]["location"] == "Remote"


def test_greenhouse_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(companies, "fetch_json", lambda url, **_k: (_ for _ in ()).throw(OSError("x")))

    assert companies.collect_greenhouse("Acme", "acme").status == "failed"


def test_ashby_maps_fields(stub_json) -> None:
    stub_json(
        {
            "jobs": [
                {
                    "title": "Senior Swift Engineer",
                    "jobUrl": "https://jobs.ashbyhq.com/acme/1",
                    "id": "a1",
                    "descriptionPlain": "text",
                    "location": "Kyiv",
                },
                {"title": "Designer", "jobUrl": "https://jobs.ashbyhq.com/acme/2"},
            ]
        }
    )

    result = companies.collect_ashby("Acme", "acme")

    assert result.items_scanned == 2
    assert [job["source_job_id"] for job in result.jobs] == ["a1"]


def test_ashby_handles_empty_board(stub_json) -> None:
    stub_json({"jobs": []})

    result = companies.collect_ashby("Acme", "acme")

    assert result.status == "healthy"
    assert result.items_scanned == 0


def test_ashby_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(companies, "fetch_json", lambda url, **_k: (_ for _ in ()).throw(OSError("x")))

    assert companies.collect_ashby("Acme", "acme").status == "failed"


def test_lever_maps_fields(stub_json) -> None:
    stub_json(
        [
            {
                "text": "iOS Developer",
                "hostedUrl": "https://jobs.lever.co/acme/1",
                "id": "l1",
                "categories": {"location": "Kyiv"},
                "createdAt": 1700000000,
            },
            {"text": "Sales Manager", "hostedUrl": "https://jobs.lever.co/acme/2"},
        ]
    )

    result = companies.collect_lever("Acme", "acme")

    assert result.items_scanned == 2
    assert result.jobs[0]["location"] == "Kyiv"


def test_lever_handles_unexpected_payload(stub_json) -> None:
    stub_json({"not": "a list"})

    result = companies.collect_lever("Acme", "acme")

    assert result.items_scanned == 0
    assert result.status == "healthy"


def test_lever_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(companies, "fetch_json", lambda url, **_k: (_ for _ in ()).throw(OSError("x")))

    assert companies.collect_lever("Acme", "acme").status == "failed"


_JOBS_MD = """# Acme

| Title | Department | Location | Type | Salary | Posted | Details |
|-------|-----------|----------|------|--------|--------|---------|
| iOS Engineer | Mobile | Ukraine (Remote) | Full-time | — | 2026-07-13 | [View](https://apply.workable.com/acme/j/1.md) |
| Backend Engineer | Core | Ukraine | Full-time | — | 2026-07-13 | [View](https://apply.workable.com/acme/j/2.md) |
| Swift Engineer | Mobile | Kyiv | Full-time | — | 2026-07-13 | no link |
| short | row |
"""


def test_workable_jobs_md_parses_table(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(companies, "fetch_text", lambda url, **_k: _JOBS_MD)

    result = companies.collect_workable_jobs_md("Acme", "acme")

    assert result.items_scanned == 3
    assert [job["title"] for job in result.jobs] == ["iOS Engineer", "Swift Engineer"]
    assert result.jobs[0]["url"] == "https://apply.workable.com/acme/j/1.md"
    assert result.jobs[0]["location"] == "Ukraine (Remote)"
    assert result.jobs[1]["url"] == ""


def test_workable_jobs_md_reports_zero_for_search_document(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        companies,
        "fetch_text",
        lambda url, **_k: "# Acme\n\n> This company has 118 open positions.\n\n## How to Search\n",
    )

    result = companies.collect_workable_jobs_md("Acme", "acme")

    assert result.items_scanned == 0
    assert result.jobs == []


def test_workable_jobs_md_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(companies, "fetch_text", lambda url, **_k: (_ for _ in ()).throw(OSError("x")))

    assert companies.collect_workable_jobs_md("Acme", "acme").status == "failed"
