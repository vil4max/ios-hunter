from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from analytics.metrics import summarize_funnel
from integrations.telegram import send_message
from planner.plan import DailyPlan, ProjectCard

_KYIV = ZoneInfo("Europe/Kyiv")


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


def notify_daily_dashboard(
    plan: DailyPlan,
    *,
    board_url: str = "",
    now: datetime | None = None,
) -> None:
    send_message(format_daily_dashboard(plan, board_url=board_url, now=now))
