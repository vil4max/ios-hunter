from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from config.settings import ACTIVE_PIPELINE_STATUSES, Settings
from database.email_seen import (
    default_email_seen_path,
    is_processed,
    load_email_seen,
    mark_processed,
    save_email_seen,
)
from integrations.email_imap import InboundMail, credentials_configured, fetch_recent_mail
from integrations.mail_classify import (
    KIND_APPLICATION_ACK,
    KIND_IGNORE,
    KIND_REJECTED_HR,
    KIND_REPLIED,
    KIND_SCREENING,
    MailEvent,
    classify_mail,
)
from parser.normalize import normalize_token
from planner.plan import ProjectCard, load_cards_from_github
from project_sync.github_client import GitHubClient, ProjectMeta


_STATUS_RANK = {
    "Inbox": 0,
    "Applied": 1,
    "Replied": 2,
    "Interview": 3,
    "Offer": 4,
}


@dataclass(frozen=True)
class MailSyncMutation:
    event: MailEvent
    card: ProjectCard | None
    action: str
    previous_status: str
    new_status: str
    item_id: str = ""
    unmatched: bool = False


@dataclass
class MailSyncResult:
    fetched: int = 0
    skipped_seen: int = 0
    ignored: int = 0
    mutations: list[MailSyncMutation] | None = None
    dry_run: bool = False


def _company_key(value: str) -> str:
    return normalize_token(value)


def _title_overlap(role_hint: str, title: str) -> float:
    hint_tokens = {t for t in normalize_token(role_hint).split() if len(t) > 2}
    title_tokens = {t for t in normalize_token(title).split() if len(t) > 2}
    if not hint_tokens or not title_tokens:
        return 0.0
    return len(hint_tokens & title_tokens) / len(hint_tokens)


def match_card(event: MailEvent, cards: list[ProjectCard]) -> ProjectCard | None:
    company = _company_key(event.company)
    if not company:
        return None

    active = [
        card
        for card in cards
        if not card.is_archived
        and _company_key(card.company) == company
        and card.status in ACTIVE_PIPELINE_STATUSES
    ]
    pool = active or [
        card
        for card in cards
        if not card.is_archived and _company_key(card.company) == company
    ]
    if not pool:
        aliases = {
            "welltech": {"well tech"},
        }
        extra = aliases.get(company, set())
        pool = [
            card
            for card in cards
            if not card.is_archived
            and (
                _company_key(card.company) in extra
                or company in _company_key(card.company)
                or _company_key(card.company) in company
            )
        ]
        pool = [c for c in pool if c.status in ACTIVE_PIPELINE_STATUSES] or pool

    if not pool:
        return None
    if len(pool) == 1:
        return pool[0]

    if event.role_hint:
        scored = sorted(
            pool,
            key=lambda card: _title_overlap(event.role_hint, card.title),
            reverse=True,
        )
        best = scored[0]
        if _title_overlap(event.role_hint, best.title) >= 0.4:
            return best
    return None


def _rank(status: str) -> int:
    return _STATUS_RANK.get(status, -1)


def plan_transition(event: MailEvent, card: ProjectCard) -> tuple[str, str, str | None, str | None]:
    """Return (action, new_status, close_reason, closed_stage). action=noop|update."""
    current = card.status

    if event.kind == KIND_APPLICATION_ACK:
        if current == "Inbox" or _rank(current) < _rank("Applied"):
            return "update", "Applied", None, None
        return "noop", current, None, None

    if event.kind == KIND_REPLIED:
        if current in {"Inbox", "Applied"}:
            return "update", "Replied", None, None
        return "noop", current, None, None

    if event.kind == KIND_SCREENING:
        if current in {"Inbox", "Applied", "Replied"}:
            return "update", "Interview", None, None
        return "noop", current, None, None

    if event.kind == KIND_REJECTED_HR:
        if current in ACTIVE_PIPELINE_STATUSES and event.confidence >= 0.9:
            closed_stage = current
            return "update", "Archived", "Rejected HR", closed_stage
        return "noop", current, None, None

    return "noop", current, None, None


def _append_mail_note(body: str, *, today: date, event: MailEvent, new_status: str) -> str:
    note = (
        f"{today.isoformat()}: email sync ({event.kind}) → {new_status}: "
        f"{event.subject or event.snippet}"
    )
    text = (body or "").rstrip()
    if note in text:
        return text + "\n"
    if text:
        return f"{text}\n\n{note}\n"
    return f"{note}\n"


def _set_select(
    client: GitHubClient,
    meta: ProjectMeta,
    item_id: str,
    field_name: str,
    option_name: str,
) -> None:
    if field_name == "Status":
        field = meta.status_field
    else:
        field = meta.fields_by_name.get(field_name)
    if not field:
        return
    option_id = field.options.get(option_name)
    if not option_id:
        return
    client.set_single_select_field(
        project_id=meta.project_id,
        item_id=item_id,
        field_id=field.id,
        option_id=option_id,
    )


def apply_card_fields(
    client: GitHubClient,
    meta: ProjectMeta,
    card: ProjectCard,
    event: MailEvent,
    *,
    new_status: str,
    close_reason: str | None,
    closed_stage: str | None,
    today: date | None = None,
) -> None:
    stamp = today or date.today()
    if new_status != "Archived":
        _set_select(client, meta, card.item_id, "Status", new_status)
    if close_reason:
        _set_select(client, meta, card.item_id, "Close Reason", close_reason)
    if closed_stage:
        _set_select(client, meta, card.item_id, "Closed Stage", closed_stage)

    if new_status == "Applied" and card.applied_at is None:
        applied_field = meta.fields_by_name.get("Applied At")
        if applied_field:
            client.set_date_field(
                project_id=meta.project_id,
                item_id=card.item_id,
                field_id=applied_field.id,
                date_value=stamp.isoformat(),
            )

    if event.recruiter:
        recruiter_field = meta.fields_by_name.get("Recruiter")
        if recruiter_field:
            client.set_text_field(
                project_id=meta.project_id,
                item_id=card.item_id,
                field_id=recruiter_field.id,
                text=event.recruiter[:1024],
            )

    draft_id = client.draft_issue_id_for_item(meta.project_id, card.item_id)
    if draft_id:
        client.update_draft_issue(
            draft_id,
            body=_append_mail_note(
                card.body,
                today=stamp,
                event=event,
                new_status=new_status,
            ),
        )
    if new_status == "Archived":
        client.archive_project_item(meta.project_id, card.item_id)
        card.is_archived = True


def apply_event(
    settings: Settings,
    event: MailEvent,
    card: ProjectCard,
    *,
    dry_run: bool = False,
    client: GitHubClient | None = None,
    meta: ProjectMeta | None = None,
) -> MailSyncMutation:
    action, new_status, close_reason, closed_stage = plan_transition(event, card)
    if action == "noop":
        return MailSyncMutation(
            event=event,
            card=card,
            action="noop",
            previous_status=card.status,
            new_status=card.status,
            item_id=card.item_id,
        )

    if dry_run:
        return MailSyncMutation(
            event=event,
            card=card,
            action="would_update",
            previous_status=card.status,
            new_status=new_status,
            item_id=card.item_id,
        )

    gh = client or GitHubClient(settings.github_token)
    project_meta = meta or gh.resolve_project(settings.project_owner, settings.project_number)
    apply_card_fields(
        gh,
        project_meta,
        card,
        event,
        new_status=new_status,
        close_reason=close_reason,
        closed_stage=closed_stage,
    )
    return MailSyncMutation(
        event=event,
        card=card,
        action="updated",
        previous_status=card.status,
        new_status=new_status,
        item_id=card.item_id,
    )


def process_mail_event(
    settings: Settings,
    event: MailEvent,
    cards: list[ProjectCard],
    *,
    dry_run: bool = False,
    client: GitHubClient | None = None,
    meta: ProjectMeta | None = None,
) -> MailSyncMutation:
    if event.kind == KIND_IGNORE:
        return MailSyncMutation(
            event=event,
            card=None,
            action="ignored",
            previous_status="",
            new_status="",
        )

    card = match_card(event, cards)
    if card is None:
        return MailSyncMutation(
            event=event,
            card=None,
            action="unmatched",
            previous_status="",
            new_status="",
            unmatched=True,
        )
    return apply_event(
        settings,
        event,
        card,
        dry_run=dry_run,
        client=client,
        meta=meta,
    )


def run_mail_sync(
    settings: Settings,
    *,
    dry_run: bool = False,
    limit: int = 40,
    since_days: int = 7,
    email_seen_path: Path | None = None,
    mails: list[InboundMail] | None = None,
    cards: list[ProjectCard] | None = None,
    client: GitHubClient | None = None,
) -> MailSyncResult:
    path = email_seen_path or default_email_seen_path()
    seen = load_email_seen(path)
    result = MailSyncResult(dry_run=dry_run, mutations=[])

    if mails is None:
        if not credentials_configured():
            raise RuntimeError("IMAP not configured (need SMTP_USER + SMTP_PASS)")
        mails = fetch_recent_mail(limit=limit, since_days=since_days)

    result.fetched = len(mails)
    gh = client
    board_cards = cards
    meta: ProjectMeta | None = None
    if board_cards is None or not dry_run:
        gh = gh or GitHubClient(settings.github_token)
        if board_cards is None:
            board_cards = load_cards_from_github(gh, settings)
        if not dry_run:
            meta = gh.resolve_project(settings.project_owner, settings.project_number)

    changed_seen = False
    for mail in mails:
        if is_processed(seen, mail.message_id):
            result.skipped_seen += 1
            continue
        event = classify_mail(mail)
        mutation = process_mail_event(
            settings,
            event,
            board_cards,
            dry_run=dry_run,
            client=gh,
            meta=meta,
        )
        assert result.mutations is not None
        result.mutations.append(mutation)
        if mutation.action == "ignored":
            result.ignored += 1

        if not dry_run:
            marked = mark_processed(
                seen,
                mail.message_id,
                kind=event.kind,
                item_id=mutation.item_id or None,
                company=event.company,
                subject=event.subject,
            )
            changed_seen = changed_seen or marked

    if changed_seen and not dry_run:
        save_email_seen(path, seen)
    return result
