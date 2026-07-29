from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from collector.types import STATUS_DEGRADED, STATUS_FAILED, STATUS_HEALTHY, SourceResult
from integrations.telegram import send_message
from parser.normalize import canonicalize_url, role_key
from planner.plan import DailyPlan, ProjectCard

_KYIV = ZoneInfo("Europe/Kyiv")
_ARCHIVE_ACTIVE_YEAR = 2026
_FOCUS_LIMIT = 6
_NEW_TODAY_LIMIT = 8
_FOLLOW_UP_LIMIT = 5

_STATUS_EMOJI: dict[str, str] = {
    "Inbox": "📥",
    "Applied": "📝",
    "Replied": "💬",
    "Screening": "🔎",
    "Post-Screen": "🧪",
    "Technical": "⚙️",
    "Post-Tech": "🔬",
    "Archived": "📦",
}
_MISSING_BOARD_EMOJI = "⚠️"
_BOARD_STATUS_ORDER: tuple[str, ...] = (
    "Inbox",
    "Applied",
    "Replied",
    "Screening",
    "Post-Screen",
    "Technical",
    "Post-Tech",
)


def status_emoji(status: str | None) -> str:
    if not status:
        return _MISSING_BOARD_EMOJI
    return _STATUS_EMOJI.get(status, "•")


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


def _card_year(card: ProjectCard) -> int | None:
    for value in (card.created_at, card.updated_at):
        if value is None:
            continue
        if value.tzinfo is not None:
            return value.astimezone(_KYIV).year
        return value.year
    if card.applied_at is not None:
        return card.applied_at.year
    return None


def split_archived_counts(
    cards: list[ProjectCard],
    *,
    active_year: int = _ARCHIVE_ACTIVE_YEAR,
) -> tuple[int, int]:
    archived_active = 0
    history = 0
    for card in cards:
        if card.status != "Archived":
            continue
        year = _card_year(card)
        if year is not None and year < active_year:
            history += 1
        else:
            archived_active += 1
    return archived_active, history


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
        if count and status not in {"Archived", "History"}:
            blocks.append(f"· {status}: {count}")
    archived_2026, history = split_archived_counts(plan.cards)
    if archived_2026 or history or plan.status_counts.get("Archived") or plan.status_counts.get("History"):
        blocks.append(f"· Archived {_ARCHIVE_ACTIVE_YEAR}: {archived_2026}")
        blocks.append(f"· History (before {_ARCHIVE_ACTIVE_YEAR}): {history}")
    if not any(v for k, v in plan.status_counts.items() if k not in {"Archived", "History"} and v):
        if not archived_2026 and not history:
            blocks.append("· —")

    blocks.append("")
    blocks.append("Daily summary")
    inbox = plan.status_counts.get("Inbox", 0)
    applied = plan.status_counts.get("Applied", 0)
    blocks.append(
        f"Inbox {inbox}, Applied {applied}, "
        f"Archived {_ARCHIVE_ACTIVE_YEAR} {archived_2026}, "
        f"History {history}, attention {len(plan.needs_attention)}, "
        f"follow-ups due {len(plan.pending_follow_ups)}."
    )
    return "\n".join(blocks)


def match_board_status(
    company: str,
    title: str,
    url: str,
    cards: list[ProjectCard],
) -> str | None:
    canon = canonicalize_url(url)
    wanted_role = role_key(company, title)
    for card in cards:
        for raw in (card.canonical_url, card.url):
            if canon and raw and canonicalize_url(raw) == canon:
                return card.status or None
        if role_key(card.company, card.title) == wanted_role:
            return card.status or None
    return None


def annotate_new_today(
    new_today: tuple[tuple[str, str, str], ...],
    cards: list[ProjectCard],
) -> list[tuple[str, str, str | None]]:
    annotated: list[tuple[str, str, str | None]] = []
    for company, title, url in new_today:
        annotated.append((company, title, match_board_status(company, title, url, cards)))
    return annotated


def _bullet_names(items: list[str], *, empty: str, limit: int) -> list[str]:
    if not items:
        return [f"  {empty}"]
    lines = [f"  {name}" for name in items[:limit]]
    if len(items) > limit:
        lines.append(f"  … +{len(items) - limit}")
    return lines


def format_full_daily_report(
    plan: DailyPlan,
    summary: CollectDaySummary,
    *,
    board_url: str = "",
    now: datetime | None = None,
) -> str:
    stamp = (now or datetime.now(_KYIV)).astimezone(_KYIV)
    lines: list[str] = [
        f"📬 Career Agent · {stamp.strftime('%d.%m.%Y')}",
        "",
        "🔍 Сбор за день",
    ]

    source_line = (
        f"✅ Источники: {summary.sources_healthy} OK"
        f" · {summary.sources_degraded} degraded"
        f" · {summary.sources_failed} fail"
        f" (из {summary.sources_total})"
    )
    lines.append(source_line)
    if summary.failed_source_names:
        lines.append("   Fail: " + ", ".join(summary.failed_source_names))
    if summary.degraded_source_names:
        lines.append("   Degraded: " + ", ".join(summary.degraded_source_names))
    lines.append(
        f"📊 Снимок: {summary.jobs_found} ролей · seen {summary.seen_total}"
    )

    annotated_new = annotate_new_today(summary.new_today, plan.cards)
    lines.extend(["", f"🆕 Новых сегодня: {summary.new_today_count}"])
    if annotated_new:
        for company, title, status in annotated_new[:_NEW_TODAY_LIMIT]:
            emoji = status_emoji(status)
            label = status or "нет карточки"
            lines.append(f"  {emoji} {company} — {title} · {label}")
        if summary.new_today_count > _NEW_TODAY_LIMIT:
            lines.append(f"  … +{summary.new_today_count - _NEW_TODAY_LIMIT}")
    else:
        lines.append("  —")

    active_bits: list[str] = []
    for status in _BOARD_STATUS_ORDER:
        count = plan.status_counts.get(status, 0)
        if count:
            active_bits.append(f"{status_emoji(status)} {status} {count}")
    lines.extend(
        [
            "",
            "🗂️ Доска",
            " · ".join(active_bits) if active_bits else "активных колонок нет",
        ]
    )

    focus = [
        f"{status_emoji(card.status)} {card.display_title} · {card.status}"
        for card in plan.today_tasks
        if card.status != "Inbox"
    ]
    lines.extend(["", "🎯 Фокус"])
    lines.extend(_bullet_names(focus, empty="нет активных задач", limit=_FOCUS_LIMIT))

    inbox_names = [
        f"{status_emoji('Inbox')} {card.display_title}"
        for card in plan.new_vacancies
    ]
    lines.extend(["", f"{status_emoji('Inbox')} Inbox"])
    lines.extend(_bullet_names(inbox_names, empty="пусто", limit=_NEW_TODAY_LIMIT))

    if plan.needs_attention:
        lines.extend(["", "⚠️ Attention"])
        lines.extend(
            _bullet_names(
                [
                    f"{status_emoji(card.status)} {card.display_title} · {card.status}"
                    for card in plan.needs_attention
                ],
                empty="нет",
                limit=_FOCUS_LIMIT,
            )
        )
    else:
        lines.extend(["", "⚠️ Attention: нет"])

    if plan.pending_follow_ups:
        lines.extend(["", "📌 Follow-up due"])
        lines.extend(
            _bullet_names(
                [
                    f"{status_emoji(card.status)} {card.display_title} · {card.status}"
                    for card in plan.pending_follow_ups
                ],
                empty="нет",
                limit=_FOLLOW_UP_LIMIT,
            )
        )
    else:
        lines.extend(["", "📌 Follow-up due: нет"])

    if plan.upcoming_interviews:
        lines.extend(["", "🎤 Interviews"])
        lines.extend(
            _bullet_names(
                [
                    f"{status_emoji(card.status)} {card.display_title} · {card.status}"
                    for card in plan.upcoming_interviews
                ],
                empty="нет",
                limit=_FOLLOW_UP_LIMIT,
            )
        )

    if board_url:
        lines.extend(["", f"🔗 {board_url}"])
    lines.append("")
    return "\n".join(lines)


def notify_daily_dashboard(
    plan: DailyPlan,
    *,
    board_url: str = "",
    now: datetime | None = None,
) -> None:
    send_message(format_daily_dashboard(plan, board_url=board_url, now=now))
