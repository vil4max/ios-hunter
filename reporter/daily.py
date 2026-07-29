from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from analytics.metrics import summarize_funnel
from collector.types import STATUS_DEGRADED, STATUS_FAILED, STATUS_HEALTHY, SourceResult
from integrations.telegram import send_message
from planner.plan import DailyPlan, ProjectCard

_KYIV = ZoneInfo("Europe/Kyiv")


@dataclass(frozen=True)
class CollectDaySummary:
    new_today_count: int
    new_today: tuple[tuple[str, str, str], ...] = ()
    seen_total: int = 0
    sources_total: int = 0
    sources_healthy: int = 0
    sources_degraded: int = 0
    sources_failed: int = 0
    jobs_found: int = 0
    failed_source_names: tuple[str, ...] = ()
    degraded_source_names: tuple[str, ...] = ()


def _card_line(card: ProjectCard) -> str:
    link = card.issue_url or card.url or card.canonical_url
    status = card.status
    badge = f" · offer:{card.offer_probability}" if card.offer_probability else ""
    if link:
        return f"· [{status}] {card.display_title}{badge}\n  {link}"
    return f"· [{status}] {card.display_title}{badge}"


def _section(title: str, cards: list[ProjectCard], *, limit: int = 12) -> list[str]:
    lines = [title]
    if not cards:
        lines.append("· —")
        return lines
    for card in cards[:limit]:
        lines.append(_card_line(card))
    if len(cards) > limit:
        lines.append(f"· … +{len(cards) - limit}")
    return lines


def _parse_seen_day(value: str | None, *, tz: ZoneInfo = _KYIV) -> date | None:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=ZoneInfo("UTC"))
    return stamp.astimezone(tz).date()


def build_collect_day_summary(
    seen: dict[str, dict[str, Any]],
    source_results: list[SourceResult],
    *,
    now: datetime | None = None,
) -> CollectDaySummary:
    stamp = (now or datetime.now(_KYIV)).astimezone(_KYIV)
    today = stamp.date()
    new_rows: list[tuple[str, str, str]] = []
    for url, meta in seen.items():
        if _parse_seen_day(str(meta.get("first_seen") or "")) != today:
            continue
        company = str(meta.get("company") or "").strip() or "—"
        title = str(meta.get("title") or "").strip() or "—"
        new_rows.append((company, title, url))
    new_rows.sort(key=lambda row: (row[0].lower(), row[1].lower(), row[2]))

    healthy = 0
    degraded = 0
    failed = 0
    jobs_found = 0
    failed_names: list[str] = []
    degraded_names: list[str] = []
    for source in source_results:
        jobs_found += len(source.jobs)
        if source.status == STATUS_FAILED:
            failed += 1
            failed_names.append(source.source_name)
        elif source.status == STATUS_DEGRADED:
            degraded += 1
            degraded_names.append(source.source_name)
        elif source.status == STATUS_HEALTHY:
            healthy += 1
        else:
            healthy += 1

    return CollectDaySummary(
        new_today_count=len(new_rows),
        new_today=tuple(new_rows),
        seen_total=len(seen),
        sources_total=len(source_results),
        sources_healthy=healthy,
        sources_degraded=degraded,
        sources_failed=failed,
        jobs_found=jobs_found,
        failed_source_names=tuple(failed_names),
        degraded_source_names=tuple(degraded_names),
    )


def format_collect_day_summary(summary: CollectDaySummary, *, limit: int = 40) -> str:
    lines = [
        "Collect summary (today)",
        f"· New in seen today: {summary.new_today_count}",
        f"· Seen total: {summary.seen_total}",
        (
            f"· Sources: {summary.sources_healthy} healthy / "
            f"{summary.sources_degraded} degraded / "
            f"{summary.sources_failed} failed "
            f"(of {summary.sources_total})"
        ),
        f"· Jobs parsed this snapshot: {summary.jobs_found}",
    ]
    if summary.failed_source_names:
        lines.append("· Failed: " + ", ".join(summary.failed_source_names))
    if summary.degraded_source_names:
        lines.append("· Degraded: " + ", ".join(summary.degraded_source_names))
    if summary.new_today:
        lines.append("")
        lines.append("New vacancies today")
        for company, title, url in summary.new_today[:limit]:
            lines.append(f"· {company} — {title}")
            lines.append(f"  {url}")
        if summary.new_today_count > limit:
            lines.append(f"· … +{summary.new_today_count - limit}")
    return "\n".join(lines)


def format_daily_dashboard(
    plan: DailyPlan,
    *,
    board_url: str = "",
    now: datetime | None = None,
) -> str:
    stamp = (now or datetime.now(_KYIV)).astimezone(_KYIV)
    blocks: list[str] = [f"Career Agent · {stamp.strftime('%Y-%m-%d')}"]
    if board_url:
        blocks.append(board_url)

    blocks.append("")
    blocks.extend(_section("New vacancies", plan.new_vacancies))
    blocks.append("")
    blocks.extend(_section("Needs attention", plan.needs_attention))
    blocks.append("")
    blocks.extend(_section("Today's tasks", plan.today_tasks[:15], limit=15))
    blocks.append("")
    blocks.extend(_section("Upcoming interviews", plan.upcoming_interviews))
    blocks.append("")
    blocks.extend(_section("Pending follow-ups", plan.pending_follow_ups))

    blocks.append("")
    blocks.append("Pipeline statistics")
    for status, count in plan.status_counts.items():
        if count:
            blocks.append(f"· {status}: {count}")
    if not any(plan.status_counts.values()):
        blocks.append("· —")

    blocks.append("")
    blocks.append("Daily summary")
    blocks.append(summarize_funnel(plan))
    return "\n".join(blocks)


def format_full_daily_report(
    plan: DailyPlan,
    summary: CollectDaySummary,
    *,
    board_url: str = "",
    now: datetime | None = None,
) -> str:
    dashboard = format_daily_dashboard(plan, board_url=board_url, now=now)
    collect = format_collect_day_summary(summary)
    return f"{dashboard}\n\n{collect}\n"


def notify_daily_dashboard(
    plan: DailyPlan,
    *,
    board_url: str = "",
    now: datetime | None = None,
) -> None:
    send_message(format_daily_dashboard(plan, board_url=board_url, now=now))
