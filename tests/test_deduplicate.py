from __future__ import annotations

from parser.deduplicate import deduplicate
from parser.normalize import normalize_title, role_key
from tests.conftest import make_vacancy


def test_normalize_title_strips_reference_suffix() -> None:
    assert normalize_title("Lead iOS Engineer (#5458)") == "lead ios engineer"
    assert normalize_title("Senior iOS Developer") == "senior ios developer"


def test_role_key_ignores_reference_suffix() -> None:
    assert role_key("N-iX", "Lead iOS Engineer (#5458)") == role_key("N-iX", "Lead iOS Engineer")


def test_deduplicate_removes_same_identity_vacancies() -> None:
    first = make_vacancy(url="https://example.com/job/1")
    duplicate = make_vacancy(url="https://example.com/job/1/?utm_source=telegram&utm_medium=bot")
    other = make_vacancy(title="Staff iOS Engineer", url="https://example.com/job/3")

    unique, removed = deduplicate([first, duplicate, other])

    assert removed == 1
    assert len(unique) == 2
    assert unique[0] is first
    assert unique[1] is other


def test_deduplicate_merges_same_role_from_multiple_sources() -> None:
    swift = make_vacancy(
        company="N-iX",
        title="Lead iOS Engineer (#5458)",
        url="https://careers.n-ix.com/jobs/4494044101-ios-leader/",
        source="company",
        source_job_id="4912838101",
        location="Ukraine",
        description="SwiftUI, UIKit, and leadership experience required",
    )
    greenhouse = make_vacancy(
        company="N-iX",
        title="Lead iOS Engineer",
        url="https://careers.n-ix.com/jobs/4912838101?gh_jid=4912838101",
        source="company",
        source_job_id="4912838101",
        location=None,
        description=None,
    )

    unique, removed = deduplicate([swift, greenhouse])

    assert removed == 1
    assert len(unique) == 1
    assert unique[0] is swift


def test_deduplicate_keeps_unique_vacancies() -> None:
    vacancies = [
        make_vacancy(title="Senior iOS Developer", url="https://example.com/job/1"),
        make_vacancy(title="Lead iOS Engineer", url="https://example.com/job/2"),
        make_vacancy(title="Principal iOS Engineer", url="https://example.com/job/3"),
    ]

    unique, removed = deduplicate(vacancies)

    assert removed == 0
    assert unique == vacancies


def test_deduplicate_handles_empty_list() -> None:
    unique, removed = deduplicate([])

    assert unique == []
    assert removed == 0
