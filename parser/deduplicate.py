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
    unique, removed, _ = deduplicate_with_report(vacancies)
    return unique, removed


def deduplicate_with_report(vacancies: list[Vacancy]) -> tuple[list[Vacancy], int, dict]:
    by_identity: dict[str, Vacancy] = {}
    groups: dict[str, list[Vacancy]] = {}
    role_to_identity: dict[tuple[str, str], str] = {}
    removed = 0

    for vacancy in vacancies:
        key = vacancy.identity_key or vacancy.hash
        existing = by_identity.get(key)
        if existing is not None:
            by_identity[key] = _pick_richer(existing, vacancy)
            groups[key].append(vacancy)
            removed += 1
            continue

        role = role_key(vacancy.company, vacancy.title)
        mapped_key = role_to_identity.get(role)
        if mapped_key is not None:
            existing = by_identity[mapped_key]
            by_identity[mapped_key] = _pick_richer(existing, vacancy)
            groups[mapped_key].append(vacancy)
            removed += 1
            continue

        by_identity[key] = vacancy
        groups[key] = [vacancy]
        role_to_identity[role] = key

    strategy_counts: dict[str, int] = {}
    duplicate_groups: list[dict] = []
    for key, items in groups.items():
        strategies = {item.identity_strategy or "unknown" for item in items}
        if len(items) > 1 and len(strategies) > 1:
            strategy = "role_key"
        else:
            strategy = (items[0].identity_strategy or "unknown") if items else "unknown"
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        if len(items) <= 1:
            continue
        duplicate_groups.append(
            {
                "identity_key": key,
                "count": len(items),
                "strategy": strategy,
                "items": [
                    {
                        "company": v.company,
                        "title": v.title,
                        "source": v.source,
                        "source_job_id": v.source_job_id,
                        "url": v.url,
                        "canonical_url": v.canonical_url,
                    }
                    for v in items
                ],
            }
        )

    report = {
        "input_count": len(vacancies),
        "unique_count": len(by_identity),
        "duplicates_collapsed": removed,
        "identity_strategies": strategy_counts,
        "duplicate_groups": duplicate_groups,
    }
    return list(by_identity.values()), removed, report
