from __future__ import annotations

from datetime import date

from config.settings import Settings
from planner.plan import (
    ARCHIVE_HISTORY_MIN_DAYS,
    ProjectCard,
    is_stale_archived,
    load_cards_from_github,
)
from project_sync.github_client import GitHubClient, ProjectMeta


def find_stale_archived_cards(
    cards: list[ProjectCard],
    *,
    today: date | None = None,
    min_days: int = ARCHIVE_HISTORY_MIN_DAYS,
) -> list[ProjectCard]:
    stamp = today or date.today()
    stale = [card for card in cards if is_stale_archived(card, stamp, min_days=min_days)]
    stale.sort(key=lambda card: (card.display_title.lower(), card.item_id))
    return stale


def migrate_archived_to_history(
    settings: Settings,
    *,
    client: GitHubClient | None = None,
    cards: list[ProjectCard] | None = None,
    today: date | None = None,
    min_days: int = ARCHIVE_HISTORY_MIN_DAYS,
    apply: bool = True,
    meta: ProjectMeta | None = None,
) -> list[ProjectCard]:
    gh = client or GitHubClient(settings.github_token)
    if cards is None:
        cards = load_cards_from_github(gh, settings)
    stale = find_stale_archived_cards(cards, today=today, min_days=min_days)
    if not apply or not stale:
        return stale

    project_meta = meta or gh.resolve_project(settings.project_owner, settings.project_number)
    status_field = project_meta.status_field
    if status_field is None:
        raise RuntimeError("Project Status field missing")
    history_option = status_field.options.get("History")
    if not history_option:
        raise RuntimeError("Project Status option History missing")

    for card in stale:
        gh.set_single_select_field(
            project_id=project_meta.project_id,
            item_id=card.item_id,
            field_id=status_field.id,
            option_id=history_option,
        )
    return stale
