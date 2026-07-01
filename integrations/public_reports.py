from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from database.repository import JobRepository


def _week_id(when: datetime | None = None) -> str:
    when = when or datetime.now(timezone.utc)
    year, week, _ = when.isocalendar()
    return f"{year}-week-{week:02d}"


def _weekly_activity(repo: JobRepository) -> tuple[int, int, int, int]:
    from_metrics = repo.weekly_activity_from_metrics()
    if from_metrics is not None:
        return from_metrics
    return repo.weekly_activity_from_history()


def generate_weekly_report(repo: JobRepository, root: Path) -> Path:
    new_jobs, closed_jobs, reopened_jobs, updated_jobs = _weekly_activity(repo)
    open_jobs = len(repo.list_open_jobs())
    remote_counts = repo.count_open_by_remote()
    remote = remote_counts.get("remote", 0)
    hybrid = remote_counts.get("hybrid", 0)
    onsite = remote_counts.get("onsite", 0)
    top_companies = repo.top_open_companies(limit=10)
    notable = repo.recent_notable_changes(days=7, limit=10)

    week = _week_id()
    lines = [
        f"# iOS Market Report — {week}",
        "",
        "## Summary",
        f"- New jobs: {new_jobs}",
        f"- Closed jobs: {closed_jobs}",
        f"- Reopened: {reopened_jobs}",
        f"- Updated: {updated_jobs}",
        f"- Currently open: {open_jobs}",
        f"- Remote: {remote} | Hybrid: {hybrid} | Onsite: {onsite}",
        "",
        "## Top Hiring Companies",
        "",
        "| Company | Open roles |",
        "| --- | ---: |",
    ]
    for company, count in top_companies:
        lines.append(f"| {company} | {count} |")

    if notable:
        lines.extend(["", "## Notable changes", ""])
        for row in notable:
            lines.append(
                f"- {row['company']}: {row['change_type']} — {row['title']} ({row['date'][:10]})"
            )

    content = "\n".join(lines) + "\n"
    weekly_dir = root / "reports" / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    output = weekly_dir / f"{week}.md"
    latest = weekly_dir / "latest.md"
    output.write_text(content, encoding="utf-8")
    latest.write_text(content, encoding="utf-8")
    return output


def generate_companies_report(repo: JobRepository, root: Path) -> Path:
    stats = repo.company_lifetime_stats(limit=20)
    lines = [
        "# Company Statistics",
        "",
        "| Company | Open | This year | Avg lifetime (days) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in stats:
        avg_days = int(row["avg_lifetime_days"] or 0)
        lines.append(
            f"| {row['company']} | {row['open_jobs']} | {row['jobs_this_year']} | {avg_days} |"
        )

    output_dir = root / "reports" / "companies"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "index.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def generate_rss(repo: JobRepository, output_path: Path, site_url: str = "https://vil4max.github.io/ios-hunter") -> None:
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "iOS Hunter — Ukrainian iOS Jobs"
    SubElement(channel, "link").text = site_url
    SubElement(channel, "description").text = "Actionable iOS and Swift vacancies"

    rows = repo.recent_actionable_activity(limit=50)

    for row in rows:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = f"{row['activity_type'].title()} — {row['company']} — {row['title']}"
        SubElement(item, "link").text = row["url"]
        SubElement(item, "guid").text = row["url"]
        SubElement(item, "pubDate").text = row["created_at"]
        SubElement(item, "description").text = f"{row['activity_type']} iOS vacancy at {row['company']}"

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(rss, encoding="unicode")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml, encoding="utf-8")


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")
