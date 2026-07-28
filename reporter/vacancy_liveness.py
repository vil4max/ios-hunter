from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from integrations.telegram import send_message
from project_sync.liveness import ClosedVacancyHit, LivenessResult

_KYIV = ZoneInfo("Europe/Kyiv")


def _card_label(hit: ClosedVacancyHit) -> str:
    company = (hit.card.company or "").strip()
    title = (hit.card.title or "").strip()
    if company and title:
        if title.lower().startswith((company + " — ").lower()):
            return title
        return f"{company} — {title}"
    return title or company or hit.card.display_title


def format_vacancy_liveness_report(
    result: LivenessResult,
    *,
    board_url: str = "",
    now: datetime | None = None,
) -> str:
    stamp = (now or datetime.now(_KYIV)).astimezone(_KYIV)
    clock = stamp.strftime("%Y-%m-%d %H:%M")
    archived = list(result.archived or [])
    closed = list(result.closed or [])
    hits = archived or closed

    if not hits:
        lines = [
            "✅ Отправлено в архив: 0",
            "",
            f"🕐 {clock}",
        ]
        return "\n".join(lines)

    if archived:
        header = f"🗂️ Отправлено в архив: {len(archived)}"
    else:
        header = f"⚠️ Найдено закрытых: {len(closed)}"

    lines = [header, ""]
    for index, hit in enumerate(hits, start=1):
        lines.append(f"{index}. {_card_label(hit)}")
        if hit.probe.reason:
            lines.append(f"   └ {hit.probe.reason}")
        if hit.card.url or hit.card.canonical_url:
            url = (hit.card.url or hit.card.canonical_url or "").strip()
            if url:
                lines.append(f"   🔗 {url}")
        lines.append("")

    if board_url:
        lines.append(f"📋 {board_url}")
        lines.append("")
    lines.append(f"🕐 {clock}")
    return "\n".join(lines)


def notify_vacancy_liveness(
    result: LivenessResult,
    *,
    board_url: str = "",
    now: datetime | None = None,
) -> None:
    send_message(
        format_vacancy_liveness_report(
            result,
            board_url=board_url,
            now=now,
        )
    )
