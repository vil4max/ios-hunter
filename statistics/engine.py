from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from database.repository import JobRepository


@dataclass
class MarketSummary:
    open_jobs: int
    remote: int
    hybrid: int
    onsite: int
    unknown_remote: int
    new_this_week: int
    closed_this_week: int
    top_companies: list[tuple[str, int]]


def compute_market_summary(repo: JobRepository) -> MarketSummary:
    open_jobs = repo.list_open_jobs()
    remote = sum(1 for job in open_jobs if job.remote == "remote")
    hybrid = sum(1 for job in open_jobs if job.remote == "hybrid")
    onsite = sum(1 for job in open_jobs if job.remote == "onsite")
    unknown = len(open_jobs) - remote - hybrid - onsite

    new_this_week = repo._conn.execute(
        """
        SELECT COUNT(*) FROM history
        WHERE change_type = 'created'
          AND date >= datetime('now', '-7 days')
        """
    ).fetchone()[0]

    closed_this_week = repo._conn.execute(
        """
        SELECT COUNT(*) FROM history
        WHERE change_type = 'closed'
          AND date >= datetime('now', '-7 days')
        """
    ).fetchone()[0]

    company_counts = Counter(job.company for job in open_jobs)
    top_companies = company_counts.most_common(10)

    return MarketSummary(
        open_jobs=len(open_jobs),
        remote=remote,
        hybrid=hybrid,
        onsite=onsite,
        unknown_remote=unknown,
        new_this_week=int(new_this_week),
        closed_this_week=int(closed_this_week),
        top_companies=top_companies,
    )


def render_market_summary(summary: MarketSummary) -> str:
    lines = [
        "# iOS Market Snapshot",
        "",
        f"- Open jobs: {summary.open_jobs}",
        f"- New this week: {summary.new_this_week}",
        f"- Closed this week: {summary.closed_this_week}",
        f"- Remote: {summary.remote} | Hybrid: {summary.hybrid} | Onsite: {summary.onsite}",
        "",
        "## Top Hiring Companies",
        "",
    ]
    for company, count in summary.top_companies:
        lines.append(f"- {company}: {count} open")
    return "\n".join(lines)
