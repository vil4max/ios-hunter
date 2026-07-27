from __future__ import annotations

from unittest.mock import patch

from collector.dou import (
    collect_dou_ios_rss,
    parse_dou_category_rss,
    parse_rss_title,
)


def test_parse_rss_title_splits_company_and_location() -> None:
    title, company, location = parse_rss_title(
        "Middle Software Engineer (IOS Native) в Sombra, Київ, Львів, віддалено"
    )

    assert title == "Middle Software Engineer (IOS Native)"
    assert company == "Sombra"
    assert location == "Київ, Львів, віддалено"


def test_parse_dou_category_rss_keeps_non_top50_and_applies_geo() -> None:
    xml = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
<item>
<title>Senior iOS Developer в Devico, віддалено</title>
<link>https://jobs.dou.ua/companies/devico/vacancies/367217/?utm_source=jobsrss</link>
</item>
<item>
<title>Lead iOS Engineer в AgileEngine, Львів, Краків (Польща), віддалено</title>
<link>https://jobs.dou.ua/companies/agileengine/vacancies/364153/</link>
</item>
<item>
<title>Business Analyst (WEB, Android, IOS) в ROZETKA, віддалено</title>
<link>https://jobs.dou.ua/companies/rozetka/vacancies/364294/</link>
</item>
<item>
<title>Backend Engineer в Acme, Київ</title>
<link>https://jobs.dou.ua/companies/acme/vacancies/1/</link>
</item>
</channel></rss>"""

    jobs = parse_dou_category_rss(xml)

    assert [job["company"] for job in jobs] == ["Devico", "ROZETKA"]
    assert jobs[0]["url"] == "https://jobs.dou.ua/companies/devico/vacancies/367217/"
    assert jobs[0]["remote"] == "remote"
    assert jobs[0]["location"] == "віддалено"


def test_collect_dou_ios_rss_reads_category_feed() -> None:
    xml = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
<item>
<title>Senior iOS Developer в Devico, віддалено</title>
<link>https://jobs.dou.ua/companies/devico/vacancies/367217/?utm_source=jobsrss</link>
</item>
<item>
<title>Principal macOS Platform Engineer в A-listware, віддалено</title>
<link>https://jobs.dou.ua/companies/a-listware/vacancies/367041/</link>
</item>
</channel></rss>"""

    with patch("collector.dou._fetch_text", return_value=xml):
        result = collect_dou_ios_rss()

    assert result.status == "healthy"
    assert result.source_id == "dou-ios-rss"
    assert result.source_name == "DOU iOS/macOS"
    assert result.items_scanned == 2
    assert {job["title"] for job in result.jobs} == {
        "Senior iOS Developer",
        "Principal macOS Platform Engineer",
    }


def test_collect_dou_ios_rss_reports_failure() -> None:
    with patch("collector.dou._fetch_text", side_effect=RuntimeError("rss down")):
        result = collect_dou_ios_rss()

    assert result.status == "failed"
    assert "rss down" in (result.error or "")
