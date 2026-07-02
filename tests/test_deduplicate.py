from __future__ import annotations

from parser.deduplicate import deduplicate
from tests.conftest import make_vacancy


def test_deduplicate_removes_same_hash_vacancies() -> None:
    first = make_vacancy(url="https://example.com/job/1")
    duplicate = make_vacancy(url="https://example.com/job/2")
    other = make_vacancy(title="Staff iOS Engineer", url="https://example.com/job/3")

    unique, removed = deduplicate([first, duplicate, other])

    assert removed == 1
    assert len(unique) == 2
    assert unique[0] is first
    assert unique[1] is other


def test_deduplicate_keeps_unique_vacancies() -> None:
    vacancies = [
        make_vacancy(title="Senior iOS Developer"),
        make_vacancy(title="Lead iOS Engineer"),
        make_vacancy(title="Principal iOS Engineer"),
    ]

    unique, removed = deduplicate(vacancies)

    assert removed == 0
    assert unique == vacancies


def test_deduplicate_handles_empty_list() -> None:
    unique, removed = deduplicate([])

    assert unique == []
    assert removed == 0
