from __future__ import annotations

from collections import defaultdict

from integrations.mail_classify import (
    KIND_APPLICATION_ACK,
    KIND_REJECTED_HR,
    KIND_REPLIED,
    KIND_SCREENING,
)
from integrations.telegram import send_message
from project_sync.mail_sync import MailSyncMutation, MailSyncResult


_KIND_ORDER = (
    KIND_REJECTED_HR,
    KIND_REPLIED,
    KIND_SCREENING,
    KIND_APPLICATION_ACK,
)

_KIND_HEADER = {
    KIND_REJECTED_HR: "❌ Отказ HR",
    KIND_REPLIED: "💬 Reply от рекрутера",
    KIND_SCREENING: "📅 Screening / interview",
    KIND_APPLICATION_ACK: "🤖 Автоответ (заявка принята)",
}


def format_imap_poll_message(
    result: MailSyncResult,
    *,
    board_url: str = "",
    unmatched_limit: int = 8,
) -> str | None:
    del board_url
    mutations = [
        m
        for m in (result.mutations or [])
        if m.action in {"updated", "would_update"}
        or (m.action == "noop" and m.card is not None and m.event.kind in _KIND_HEADER)
    ]
    if not mutations:
        return None

    by_kind: dict[str, list[MailSyncMutation]] = defaultdict(list)
    for mutation in mutations:
        kind = mutation.event.kind
        if kind not in _KIND_HEADER:
            continue
        by_kind[kind].append(mutation)

    if not by_kind:
        return None

    lines: list[str] = ["📬 Почта"]
    for kind in _KIND_ORDER:
        group = by_kind.get(kind) or []
        if not group:
            continue
        lines.append("")
        lines.append(_KIND_HEADER[kind])
        for mutation in group[:unmatched_limit]:
            lines.extend(_format_item(mutation))
        extra = len(group) - unmatched_limit
        if extra > 0:
            lines.append(f"… ещё {extra}")

    return "\n".join(lines).rstrip()


def _format_item(mutation: MailSyncMutation) -> list[str]:
    event = mutation.event
    title = _item_title(mutation)
    lines = [f"• {title}"]

    subject = (event.subject or "").strip()
    if subject and subject.lower() not in title.lower():
        lines.append(f"  {subject[:100]}")

    if mutation.action in {"updated", "would_update"}:
        arrow = f"{mutation.previous_status} → {mutation.new_status}"
        prefix = "CRM" if mutation.action == "updated" else "dry"
        lines.append(f"  ✅ {prefix}: {arrow}")
    elif mutation.action == "noop" and mutation.card is not None:
        lines.append(f"  ✓ уже на борде: {mutation.card.status}")
    elif mutation.unmatched:
        lines.append("  ⚠ нет карточки на борде")

    return lines


def _item_title(mutation: MailSyncMutation) -> str:
    if mutation.card is not None:
        return mutation.card.display_title
    event = mutation.event
    company = (event.company or "").strip()
    role = (event.role_hint or "").strip()
    if company and role:
        return f"{company} — {role}"
    if company:
        return company
    subject = (event.subject or "").strip()
    if subject:
        return subject[:90]
    return event.from_addr or "?"


def notify_imap_poll(
    result: MailSyncResult,
    *,
    board_url: str = "",
) -> bool:
    text = format_imap_poll_message(result, board_url=board_url)
    if not text:
        return False
    send_message(text)
    return True
