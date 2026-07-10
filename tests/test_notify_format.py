from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from integrations.notify import format_empty_report, format_vacancies_message, resolve_source
from tests.conftest import make_vacancy

_KYIV = ZoneInfo("Europe/Kyiv")


def test_format_header_count_and_kyiv_time() -> None:
    vacancy = make_vacancy(
        title="Senior iOS Engineer",
        company="Acme",
        url="https://jobs.ashbyhq.com/acme/123",
        source="company",
    )
    now = datetime(2026, 7, 10, 11, 47, tzinfo=_KYIV)
    message = format_vacancies_message([vacancy], now=now)
    assert message is not None
    assert message.startswith("Вакансий 1 · 2026-07-10 11:47")


def test_format_empty_report_kyiv_time_and_checked() -> None:
    now = datetime(2026, 7, 10, 18, 0, tzinfo=_KYIV)
    assert format_empty_report(checked=21, now=now) == (
        "Новых вакансий нет · 2026-07-10 18:00\n"
        "Проверено: 21"
    )


def test_format_includes_title_company_source_url() -> None:
    vacancy = make_vacancy(
        title="iOS Developer",
        company="Preply",
        url="https://jobs.ashbyhq.com/preply/abc",
        source="company",
    )
    now = datetime(2026, 7, 10, 9, 0, tzinfo=_KYIV)
    message = format_vacancies_message([vacancy], now=now)
    assert message == (
        "Вакансий 1 · 2026-07-10 09:00\n"
        "\n"
        "1. iOS Developer\n"
        "   Preply\n"
        "   Ashby\n"
        "   https://jobs.ashbyhq.com/preply/abc"
    )


def test_format_multiple_vacancies_in_one_message() -> None:
    vacancies = [
        make_vacancy(
            title="Senior iOS Engineer",
            company="Readdle",
            url="https://boards.greenhouse.io/readdle70/jobs/1",
            source="company",
        ),
        make_vacancy(
            title="Swift Developer",
            company="EPAM",
            url="https://careers.epam.com/en/vacancy/ios-1",
            source="company",
        ),
    ]
    now = datetime(2026, 7, 10, 15, 30, tzinfo=_KYIV)
    message = format_vacancies_message(vacancies, now=now)
    assert message == (
        "Вакансий 2 · 2026-07-10 15:30\n"
        "\n"
        "1. Senior iOS Engineer\n"
        "   Readdle\n"
        "   Greenhouse\n"
        "   https://boards.greenhouse.io/readdle70/jobs/1\n"
        "\n"
        "2. Swift Developer\n"
        "   EPAM\n"
        "   EPAM careers\n"
        "   https://careers.epam.com/en/vacancy/ios-1"
    )


def test_format_returns_none_for_zero_vacancies() -> None:
    assert format_vacancies_message([]) is None


def test_format_deduplicates_same_url() -> None:
    first = make_vacancy(
        title="iOS Engineer",
        company="Acme",
        url="https://example.com/jobs/1?utm_source=x",
        source="company",
    )
    second = make_vacancy(
        title="iOS Engineer (repost)",
        company="Acme",
        url="https://example.com/jobs/1",
        source="company",
    )
    now = datetime(2026, 7, 10, 12, 0, tzinfo=_KYIV)
    message = format_vacancies_message([first, second], now=now)
    assert message is not None
    assert message.startswith("Вакансий 1 ·")
    assert "iOS Engineer (repost)" not in message
    assert message.count("https://example.com/jobs/1") == 1


def test_resolve_source_from_raw_and_url() -> None:
    assert resolve_source(make_vacancy(source="dou", url="https://jobs.dou.ua/x")) == "DOU"
    assert resolve_source(
        make_vacancy(company="DataArt", source="company", url="https://www.dataart.team/vacancies/ios")
    ) == "DataArt careers"
    assert resolve_source(
        make_vacancy(company="GlobalLogic", source="company", url="https://www.globallogic.com/ua/careers/x")
    ) == "GlobalLogic careers"
    assert resolve_source(
        make_vacancy(company="MacPaw", source="company", url="https://macpaw.com/careers/ios")
    ) == "MacPaw careers"


def test_preserves_exact_title() -> None:
    vacancy = make_vacancy(
        title="Senior iOS Engineer (SwiftUI / UIKit)",
        company="Acme",
        url="https://jobs.lever.co/acme/1",
        source="company",
    )
    now = datetime(2026, 1, 1, 0, 0, tzinfo=_KYIV)
    message = format_vacancies_message([vacancy], now=now)
    assert message is not None
    assert "1. Senior iOS Engineer (SwiftUI / UIKit)" in message
    assert "Lever" in message
