from __future__ import annotations

from parser.normalize import Vacancy, role_key


def _richness_score(vacancy: Vacancy) -> int:
    score = 0
    if vacancy.description:
        score += len(vacancy.description)
    if vacancy.location:
        score += 10
    if vacancy.published_at:
        score += 5
    if "?" not in vacancy.url:
        score += 1
    return score


def _pick_richer(first: Vacancy, second: Vacancy) -> Vacancy:
    first_score = _richness_score(first)
    second_score = _richness_score(second)
    if second_score > first_score:
        return second
    return first


def deduplicate(vacancies: list[Vacancy]) -> tuple[list[Vacancy], int]:
    by_role: dict[tuple[str, str], Vacancy] = {}
    removed = 0

    for vacancy in vacancies:
        key = role_key(vacancy.company, vacancy.title)
        existing = by_role.get(key)
        if existing is None:
            by_role[key] = vacancy
            continue
        by_role[key] = _pick_richer(existing, vacancy)
        removed += 1

    return list(by_role.values()), removed
