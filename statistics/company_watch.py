from __future__ import annotations

from dataclasses import dataclass

from database.repository import JobRepository


@dataclass
class CompanyWatchAlert:
    company: str
    open_jobs: int
    titles: list[str]
    urls: list[str]


def find_hiring_sprees(repo: JobRepository, minimum_open: int = 3) -> list[CompanyWatchAlert]:
    rows = repo._conn.execute(
        """
        SELECT company, title, url
        FROM jobs
        WHERE status = 'open'
          AND (
            lower(title) LIKE '%ios%'
            OR lower(title) LIKE '%swift%'
            OR lower(title) LIKE '%mobile%'
          )
        ORDER BY company, title
        """
    ).fetchall()

    grouped: dict[str, list[tuple[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["company"], []).append((row["title"], row["url"]))

    alerts: list[CompanyWatchAlert] = []
    for company, jobs in grouped.items():
        if len(jobs) < minimum_open:
            continue
        alerts.append(
            CompanyWatchAlert(
                company=company,
                open_jobs=len(jobs),
                titles=[title for title, _ in jobs],
                urls=[url for _, url in jobs],
            )
        )

    alerts.sort(key=lambda item: item.open_jobs, reverse=True)
    return alerts


def render_company_watch(alerts: list[CompanyWatchAlert]) -> str:
    if not alerts:
        return ""

    lines = ["Company Watch", "", "Companies with 3+ open mobile/iOS roles:", ""]
    for alert in alerts:
        lines.append(f"• {alert.company} — {alert.open_jobs} roles")
        for title, url in zip(alert.titles[:5], alert.urls[:5]):
            lines.append(f"  - {title}")
            lines.append(f"    {url}")
        if alert.open_jobs > 5:
            lines.append(f"  … and {alert.open_jobs - 5} more")
        lines.append("")
    lines.append("Consider reaching out to a recruiter directly.")
    return "\n".join(lines).strip()
