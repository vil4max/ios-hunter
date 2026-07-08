from __future__ import annotations

from unittest.mock import patch

from collector.dou import (
    _build_company_matchers,
    _parse_company_vacancies,
    _parse_rss_items,
    collect_dou_top50,
    load_top50_companies,
    match_top50_company,
)


TOP50_CSV = """date,rate,company,isDouData,cities,staffTotal,staffTech,openPositions
01-2026,1,EPAM Ukraine,,,1000,,10
01-2026,2,SoftServe,,,900,,8
01-2026,3,Uklon,,,500,,3
"""


def test_load_top50_companies_reads_latest_snapshot() -> None:
    with patch("collector.dou.discover_top50_csv_filename", return_value="top50-2026-01_v2.csv"):
        with patch("collector.dou._fetch_text", return_value=TOP50_CSV):
            companies = load_top50_companies(session=object())  # type: ignore[arg-type]

    assert companies == ["EPAM Ukraine", "SoftServe", "Uklon"]


def test_match_top50_company_handles_aliases() -> None:
    matchers = _build_company_matchers(["EPAM Ukraine", "GlobalLogic Ukraine", "Uklon"])

    assert match_top50_company("EPAM", matchers) == "EPAM Ukraine"
    assert match_top50_company("GlobalLogic", matchers) == "GlobalLogic Ukraine"
    assert match_top50_company("Uklon", matchers) == "Uklon"
    assert match_top50_company("MacPaw", matchers) is None


def test_parse_company_vacancies_filters_ios_roles() -> None:
    html = """
    <a class="vt" href="https://jobs.dou.ua/companies/uklon/vacancies/363708/">iOS Engineer Senior</a>
    <a class="vt" href="https://jobs.dou.ua/companies/uklon/vacancies/363709/">Backend Engineer</a>
  """

    jobs = _parse_company_vacancies(html, "Uklon")

    assert len(jobs) == 1
    assert jobs[0]["title"] == "iOS Engineer Senior"
    assert jobs[0]["source"] == "dou"
    assert jobs[0]["source_job_id"] == "363708"


def test_parse_rss_items_matches_top50_companies() -> None:
    xml = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
<item>
<title>iOS Engineer Senior (Rider Team) в Uklon, Київ, віддалено</title>
<link>https://jobs.dou.ua/companies/uklon/vacancies/363708/?utm_source=jobsrss</link>
</item>
<item>
<title>Lead iOS Engineer в AgileEngine, Львів</title>
<link>https://jobs.dou.ua/companies/agileengine/vacancies/364153/</link>
</item>
</channel></rss>"""
    matchers = _build_company_matchers(["Uklon", "SoftServe"])

    jobs = _parse_rss_items(xml, matchers)

    assert len(jobs) == 1
    assert jobs[0]["company"] == "Uklon"
    assert jobs[0]["title"] == "iOS Engineer Senior (Rider Team)"
    assert jobs[0]["url"] == "https://jobs.dou.ua/companies/uklon/vacancies/363708/"


def test_collect_dou_top50_merges_company_pages_and_feeds() -> None:
    companies = ["Uklon", "Playtech"]
    company_html = """
    <a class="vt" href="https://jobs.dou.ua/companies/playtech/vacancies/361257/">iOS Developer</a>
    """
    rss_xml = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
<item>
<title>iOS Engineer Senior (Rider Team) в Uklon, Київ, віддалено</title>
<link>https://jobs.dou.ua/companies/uklon/vacancies/363708/?utm_source=jobsrss</link>
</item>
</channel></rss>"""

    class FakeResponse:
        def __init__(self, text: str, status_code: int = 200) -> None:
            self.text = text
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(self.status_code)

    class FakeSession:
        headers: dict[str, str] = {}

        def get(self, url: str, timeout: int = 30) -> FakeResponse:
            if url.endswith("/companies/uklon/"):
                return FakeResponse("")
            if url.endswith("/companies/playtech/"):
                return FakeResponse("")
            if url.endswith("/companies/uklon/vacancies/"):
                return FakeResponse("")
            if url.endswith("/companies/playtech/vacancies/"):
                return FakeResponse(company_html)
            if "search=Uklon" in url:
                return FakeResponse('href="https://jobs.dou.ua/companies/uklon/vacancies/"')
            if "search=Playtech" in url:
                return FakeResponse('href="https://jobs.dou.ua/companies/playtech/vacancies/"')
            raise AssertionError(url)

    with patch("collector.dou.requests.Session", return_value=FakeSession()):
        with patch("collector.dou.load_top50_companies", return_value=companies):
            with patch("collector.dou._fetch_text", return_value=rss_xml):
                with patch("collector.dou.write_career_sites_report"):
                    result = collect_dou_top50()

    assert result.status == "healthy"
    assert result.source_id == "dou-top50"
    assert len(result.jobs) == 2
    titles = {job["title"] for job in result.jobs}
    assert "iOS Developer" in titles
    assert "iOS Engineer Senior (Rider Team)" in titles
