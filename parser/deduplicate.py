from __future__ import annotations

from parser.normalize import Vacancy, compute_hash


def deduplicate(vacancies: list[Vacancy]) -> tuple[list[Vacancy], int]:
    seen_hashes: set[str] = set()
    unique: list[Vacancy] = []
    removed = 0

    for vacancy in vacancies:
        if vacancy.hash in seen_hashes:
            removed += 1
            continue
        seen_hashes.add(vacancy.hash)
        unique.append(vacancy)

    return unique, removed
