from __future__ import annotations

import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from database.repository import JobRepository


def _week_id(when: datetime | None = None) -> str:
    when = when or datetime.now(timezone.utc)
    year, week, _ = when.isocalendar()
    return f"{year}-week-{week:02d}"


def generate_weekly_report(repo: JobRepository, root: Path) -> Path:
    summary_rows = repo._conn.execute(
        """
        SELECT
            COALESCE(SUM(new_jobs), 0),
            COALESCE(SUM(closed_jobs), 0),
            COALESCE(SUM(reopened_jobs), 0),
            COALESCE(SUM(updated_jobs), 0)
        FROM run_metrics
        WHERE finished_at >= datetime('now', '-7 days')
        """
    ).fetchone()

    open_jobs = repo._conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE status = 'open'"
    ).fetchone()[0]
    remote = repo._conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE status = 'open' AND remote = 'remote'"
    ).fetchone()[0]
    hybrid = repo._conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE status = 'open' AND remote = 'hybrid'"
    ).fetchone()[0]
    onsite = repo._conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE status = 'open' AND remote = 'onsite'"
    ).fetchone()[0]

    top_companies = repo._conn.execute(
        """
        SELECT company, COUNT(*) AS cnt
        FROM jobs WHERE status = 'open'
        GROUP BY company ORDER BY cnt DESC LIMIT 10
        """
    ).fetchall()

    week = _week_id()
    lines = [
        f"# iOS Market Report — {week}",
        "",
        "## Summary",
        f"- New jobs: {summary_rows[0]}",
        f"- Closed jobs: {summary_rows[1]}",
        f"- Reopened: {summary_rows[2]}",
        f"- Updated: {summary_rows[3]}",
        f"- Currently open: {open_jobs}",
        f"- Remote: {remote} | Hybrid: {hybrid} | Onsite: {onsite}",
        "",
        "## Top Hiring Companies",
        "",
    ]
    for row in top_companies:
        lines.append(f"- {row['company']}: {row['cnt']} open")

    output = root / "reports" / "weekly" / f"{week}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def generate_rss(repo: JobRepository, output_path: Path, site_url: str = "https://vil4max.github.io/ios-hunter") -> None:
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "iOS Hunter — Ukrainian iOS Jobs"
    SubElement(channel, "link").text = site_url
    SubElement(channel, "description").text = "Actionable iOS and Swift vacancies"

    rows = repo._conn.execute(
        """
        SELECT j.company, j.title, j.url, ra.activity_type, ra.created_at
        FROM run_activity ra
        JOIN jobs j ON j.id = ra.job_id
        WHERE ra.activity_type IN ('new', 'updated', 'reopened')
        ORDER BY ra.created_at DESC
        LIMIT 50
        """
    ).fetchall()

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
