from __future__ import annotations

from integrations.telegram import send_message
from project_sync.mail_sync import MailSyncMutation, MailSyncResult


def format_imap_poll_message(
    result: MailSyncResult,
    *,
    board_url: str = "",
    unmatched_limit: int = 5,
) -> str | None:
    mutations = result.mutations or []
    updates = [
        m
        for m in mutations
        if m.action in {"updated", "would_update"}
    ]
    unmatched = [m for m in mutations if m.unmatched]

    if not updates and not unmatched:
        return None

    lines: list[str] = ["📧 Mail → CRM"]
    for mutation in updates:
        label = _card_label(mutation)
        arrow = f"{mutation.previous_status} → {mutation.new_status}"
        prefix = "·" if mutation.action == "updated" else "dry"
        lines.append(f"{prefix} {label}: {arrow}")

    for mutation in unmatched[:unmatched_limit]:
        company = mutation.event.company or mutation.event.from_addr or "?"
        kind = mutation.event.kind
        lines.append(f"· unmatched ({kind}): {company} — {mutation.event.subject[:80]}")
    if len(unmatched) > unmatched_limit:
        lines.append(f"· … +{len(unmatched) - unmatched_limit} unmatched")

    if board_url:
        lines.append(board_url)
    return "\n".join(lines)


def _card_label(mutation: MailSyncMutation) -> str:
    if mutation.card is not None:
        return mutation.card.display_title
    company = mutation.event.company or "?"
    role = mutation.event.role_hint or mutation.event.subject[:60]
    return f"{company} — {role}"


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
