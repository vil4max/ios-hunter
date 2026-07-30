from __future__ import annotations

from integrations.telegram import send_message
from project_sync.hirify_sync import HirifySyncMutation, HirifySyncResult


def format_hirify_sync_message(
    result: HirifySyncResult,
    *,
    unmatched_limit: int = 8,
) -> str | None:
    del unmatched_limit
    mutations = [
        m
        for m in (result.mutations or [])
        if m.action
        in {
            "created",
            "updated",
            "noted",
            "would_create",
            "would_update",
            "would_note",
        }
    ]
    if not mutations:
        return None

    lines = ["📋 Hirify → CRM"]
    for mutation in mutations:
        lines.extend(_format_item(mutation))
    return "\n".join(lines).rstrip()


def _format_item(mutation: HirifySyncMutation) -> list[str]:
    row = mutation.row
    title = (
        mutation.card.display_title
        if mutation.card is not None
        else f"{row.company} — {row.job_title}".strip(" —")
    )
    lines = [f"• {title}"]
    stage = (row.stage or "?").strip()
    if mutation.action in {"created", "would_create"}:
        prefix = "CRM" if mutation.action == "created" else "dry"
        lines.append(f"  ✅ {prefix}: создана → {mutation.new_status} ({stage})")
    elif mutation.action in {"updated", "would_update"}:
        prefix = "CRM" if mutation.action == "updated" else "dry"
        arrow = f"{mutation.previous_status} → {mutation.new_status}"
        lines.append(f"  ✅ {prefix}: {arrow} ({stage})")
    elif mutation.action in {"noted", "would_note"}:
        prefix = "CRM" if mutation.action == "noted" else "dry"
        lines.append(f"  📝 {prefix}: note/follow-up ({stage})")
    return lines


def notify_hirify_sync(result: HirifySyncResult) -> bool:
    text = format_hirify_sync_message(result)
    if not text:
        return False
    send_message(text)
    return True
