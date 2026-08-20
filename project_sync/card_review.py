from __future__ import annotations

from datetime import date

from planner.plan import ProjectCard
from project_sync.github_client import GitHubClient, GitHubGraphQLError, ProjectMeta


def append_archive_note(
    body: str,
    *,
    reason: str,
    note: str,
    archived_at: date | None = None,
) -> str:
    stamp = archived_at or date.today()
    detail = f": {note.strip()}" if note.strip() else ""
    line = f"{stamp.isoformat()}: owner archived ({reason}){detail}"
    text = (body or "").rstrip()
    if line in text:
        return text + "\n"
    return f"{text}\n\n{line}\n" if text else f"{line}\n"


def archive_card(
    client: GitHubClient,
    meta: ProjectMeta,
    card: ProjectCard,
    *,
    reason: str,
    note: str = "",
    archived_at: date | None = None,
) -> None:
    close_reason_field = meta.fields_by_name.get("Close Reason")
    close_reason_option = close_reason_field.options.get(reason) if close_reason_field else None
    if close_reason_field is None or close_reason_option is None:
        raise GitHubGraphQLError(f"Project Close Reason option missing: {reason}")
    closed_stage_field = meta.fields_by_name.get("Closed Stage")
    closed_stage_option = (
        closed_stage_field.options.get(card.status) if closed_stage_field else None
    )
    if closed_stage_field is None or closed_stage_option is None:
        raise GitHubGraphQLError(f"Project Closed Stage option missing: {card.status}")
    draft_id = client.draft_issue_id_for_item(meta.project_id, card.item_id)
    if not draft_id:
        raise GitHubGraphQLError("Project card is not an editable draft issue")

    client.set_single_select_field(
        project_id=meta.project_id,
        item_id=card.item_id,
        field_id=close_reason_field.id,
        option_id=close_reason_option,
    )
    client.set_single_select_field(
        project_id=meta.project_id,
        item_id=card.item_id,
        field_id=closed_stage_field.id,
        option_id=closed_stage_option,
    )
    client.update_draft_issue(
        draft_id,
        body=append_archive_note(
            card.body,
            reason=reason,
            note=note,
            archived_at=archived_at,
        ),
    )
    client.archive_project_item(meta.project_id, card.item_id)
