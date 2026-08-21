from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from config.settings import ACTIVE_PIPELINE_STATUSES, Settings
from integrations.vacancy_probe import ProbeResult, probe_vacancy_url
from planner.plan import ProjectCard, load_cards_from_github
from project_sync.github_client import GitHubClient, ProjectMeta


@dataclass(frozen=True)
class ClosedVacancyHit:
    card: ProjectCard
    probe: ProbeResult
    close_reason: str = "Role closed"


@dataclass
class LivenessResult:
    checked: int = 0
    skipped: int = 0
    closed: list[ClosedVacancyHit] | None = None
    no_reply: list[ClosedVacancyHit] | None = None
    archived: list[ClosedVacancyHit] | None = None
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.closed is None:
            self.closed = []
        if self.no_reply is None:
            self.no_reply = []
        if self.archived is None:
            self.archived = []
        if self.errors is None:
            self.errors = []


def active_cards_for_liveness(cards: list[ProjectCard]) -> list[ProjectCard]:
    return [card for card in cards if card.status in ACTIVE_PIPELINE_STATUSES]


def find_closed_vacancies(
    cards: list[ProjectCard],
    *,
    probe=probe_vacancy_url,
) -> LivenessResult:
    result = LivenessResult()
    for card in active_cards_for_liveness(cards):
        url = (card.url or card.canonical_url or "").strip()
        probe_result = probe(url, card_title=card.title)
        if probe_result.skipped:
            result.skipped += 1
            continue
        result.checked += 1
        if probe_result.closed:
            result.closed.append(ClosedVacancyHit(card=card, probe=probe_result))
    return result


def find_no_reply_applications(
    cards: list[ProjectCard],
    *,
    today: date,
    wait_days: int,
    excluded_item_ids: set[str] | frozenset[str] | None = None,
) -> list[ClosedVacancyHit]:
    excluded = excluded_item_ids or frozenset()
    hits: list[ClosedVacancyHit] = []
    for card in cards:
        if (
            card.item_id in excluded
            or card.status != "Applied"
            or card.applied_at is None
        ):
            continue
        age_days = (today - card.applied_at).days
        if age_days <= wait_days:
            continue
        url = (card.url or card.canonical_url or "").strip()
        hits.append(
            ClosedVacancyHit(
                card=card,
                probe=ProbeResult(
                    url=url,
                    closed=False,
                    skipped=False,
                    http_status=None,
                    reason=f"no reply after {age_days} days",
                ),
                close_reason="No reply",
            )
        )
    return hits


def _append_archive_note(
    body: str,
    *,
    today: date,
    close_reason: str,
    reason: str,
) -> str:
    note = f"{today.isoformat()}: auto-archived ({close_reason}): {reason}"
    text = (body or "").rstrip()
    if note in text:
        return text + "\n"
    if text:
        return f"{text}\n\n{note}\n"
    return f"{note}\n"


def archive_closed_vacancies(
    client: GitHubClient,
    hits: list[ClosedVacancyHit],
    *,
    settings: Settings | None = None,
    today: date | None = None,
    meta: ProjectMeta | None = None,
) -> list[ClosedVacancyHit]:
    if not hits:
        return []
    if meta is not None:
        project_meta = meta
    else:
        if settings is None:
            raise ValueError("settings or meta is required")
        project_meta = client.resolve_project(settings.project_owner, settings.project_number)
    close_reason_field = project_meta.fields_by_name.get("Close Reason")
    closed_stage_field = project_meta.fields_by_name.get("Closed Stage")
    stamp = today or date.today()
    archived: list[ClosedVacancyHit] = []
    for hit in hits:
        card = hit.card
        close_reason_option = (
            close_reason_field.options.get(hit.close_reason) if close_reason_field else None
        )
        if close_reason_field and close_reason_option:
            client.set_single_select_field(
                project_id=project_meta.project_id,
                item_id=card.item_id,
                field_id=close_reason_field.id,
                option_id=close_reason_option,
            )
        if closed_stage_field:
            stage_option = closed_stage_field.options.get(card.status)
            if stage_option:
                client.set_single_select_field(
                    project_id=project_meta.project_id,
                    item_id=card.item_id,
                    field_id=closed_stage_field.id,
                    option_id=stage_option,
                )
        draft_id = client.draft_issue_id_for_item(project_meta.project_id, card.item_id)
        if draft_id:
            client.update_draft_issue(
                draft_id,
                body=_append_archive_note(
                    card.body,
                    today=stamp,
                    close_reason=hit.close_reason,
                    reason=hit.probe.reason,
                ),
            )
        client.archive_project_item(project_meta.project_id, card.item_id)
        archived.append(hit)
    return archived


def run_vacancy_liveness(
    settings: Settings,
    *,
    client: GitHubClient | None = None,
    probe=probe_vacancy_url,
    today: date | None = None,
    apply_archives: bool = True,
) -> LivenessResult:
    gh = client or GitHubClient(settings.github_token)
    cards = load_cards_from_github(gh, settings)
    result = find_closed_vacancies(cards, probe=probe)
    stamp = today or date.today()
    result.no_reply = find_no_reply_applications(
        cards,
        today=stamp,
        wait_days=settings.application_no_reply_days,
        excluded_item_ids={hit.card.item_id for hit in result.closed or []},
    )
    candidates = [*(result.closed or []), *(result.no_reply or [])]
    if apply_archives and candidates:
        result.archived = archive_closed_vacancies(
            gh,
            candidates,
            settings=settings,
            today=stamp,
        )
    return result
