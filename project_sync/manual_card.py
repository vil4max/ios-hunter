from __future__ import annotations

from dataclasses import dataclass

from config.settings import Settings
from parser.normalize import canonicalize_url
from project_sync.github_client import GitHubClient, GitHubGraphQLError, ProjectMeta


@dataclass
class ManualCard:
    company: str
    title: str
    status: str
    source: str = ""
    url: str = ""
    applied_at: str | None = None
    follow_up: str | None = None
    priority: str | None = None
    offer_probability: str | None = None
    notes: str = ""


def build_draft_body(card: ManualCard) -> str:
    canonical = canonicalize_url(card.url) if card.url else ""
    lines = [
        "<!-- career-agent-manual -->",
        f"**Company:** {card.company}",
        f"**Role:** {card.title}",
    ]
    if card.source:
        lines.append(f"**Source:** {card.source}")
    if card.url:
        lines.append(f"**URL:** {card.url}")
    if canonical:
        lines.append(f"Canonical-URL: {canonical}")
    if card.notes:
        lines.append("")
        lines.append(card.notes)
    return "\n".join(lines) + "\n"


def apply_manual_fields(
    client: GitHubClient,
    meta: ProjectMeta,
    item_id: str,
    card: ManualCard,
) -> None:
    if meta.status_field:
        option_id = meta.status_field.options.get(card.status)
        if option_id:
            client.set_single_select_field(
                project_id=meta.project_id,
                item_id=item_id,
                field_id=meta.status_field.id,
                option_id=option_id,
            )

    text_values = {
        "Company": card.company,
        "Source": card.source,
        "URL": card.url,
        "Canonical URL": canonicalize_url(card.url) if card.url else "",
    }
    for field_name, value in text_values.items():
        project_field = meta.fields_by_name.get(field_name)
        if project_field and value:
            client.set_text_field(
                project_id=meta.project_id,
                item_id=item_id,
                field_id=project_field.id,
                text=value[:1024],
            )

    date_values = {
        "Applied At": card.applied_at,
        "Follow Up": card.follow_up,
    }
    for field_name, value in date_values.items():
        project_field = meta.fields_by_name.get(field_name)
        if project_field and value:
            client.set_date_field(
                project_id=meta.project_id,
                item_id=item_id,
                field_id=project_field.id,
                date_value=value,
            )

    select_values = {
        "Priority": card.priority,
        "Offer Probability": card.offer_probability,
    }
    for field_name, value in select_values.items():
        project_field = meta.fields_by_name.get(field_name)
        if not project_field or not value:
            continue
        option_id = project_field.options.get(value)
        if option_id:
            client.set_single_select_field(
                project_id=meta.project_id,
                item_id=item_id,
                field_id=project_field.id,
                option_id=option_id,
            )


def create_private_card(
    settings: Settings,
    card: ManualCard,
    *,
    client: GitHubClient | None = None,
) -> str:
    """Create a private Project draft item (not a public repo Issue)."""
    if not settings.project_owner or settings.project_number <= 0:
        raise GitHubGraphQLError("Project owner/number not configured")
    gh = client or GitHubClient(settings.github_token)
    meta = gh.resolve_project(settings.project_owner, settings.project_number)
    title = f"{card.company} — {card.title}"
    item_id = gh.add_draft_issue(meta.project_id, title=title, body=build_draft_body(card))
    apply_manual_fields(gh, meta, item_id, card)
    return item_id
