from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from config.settings import ACTIVE_PIPELINE_STATUSES, Settings
from database.hirify_seen import (
    default_hirify_seen_path,
    is_processed,
    load_hirify_seen,
    mark_processed,
    save_hirify_seen,
)
from integrations.hirify_export import (
    HirifyApplicationRow,
    latest_applications_xlsx,
    map_hirify_stage,
    parse_applications_xlsx,
)
from parser.normalize import canonicalize_url, normalize_token
from planner.plan import ProjectCard, load_cards_from_github
from project_sync.github_client import GitHubClient
from project_sync.manual_card import ManualCard, seed_seen_from_manual_card, upsert_private_card


_STATUS_RANK = {
    "Inbox": 0,
    "Applied": 1,
    "Replied": 2,
    "Interview": 3,
    "Offer": 4,
}


@dataclass(frozen=True)
class HirifySyncMutation:
    row: HirifyApplicationRow
    card: ProjectCard | None
    action: str
    previous_status: str
    new_status: str
    item_id: str = ""
    created: bool = False


@dataclass
class HirifySyncResult:
    rows: int = 0
    skipped_seen: int = 0
    mutations: list[HirifySyncMutation] | None = None
    dry_run: bool = False
    xlsx_path: str = ""


def _rank(status: str) -> int:
    return _STATUS_RANK.get(status, -1)


def _company_key(value: str) -> str:
    return normalize_token(value)


def _title_overlap(left: str, right: str) -> float:
    a = {t for t in normalize_token(left).split() if len(t) > 2}
    b = {t for t in normalize_token(right).split() if len(t) > 2}
    if not a or not b:
        return 0.0
    return len(a & b) / len(a)


def _url_keys(row: HirifyApplicationRow) -> set[str]:
    keys: set[str] = set()
    for raw in (row.job_url, row.preferred_url, row.recruiter_contact):
        key = canonicalize_url(raw) if raw else ""
        if key:
            keys.add(key)
    return keys


def match_card(row: HirifyApplicationRow, cards: list[ProjectCard]) -> ProjectCard | None:
    url_keys = _url_keys(row)
    if url_keys:
        for card in cards:
            for raw in (card.canonical_url, card.url):
                key = canonicalize_url(raw) if raw else ""
                if key and key in url_keys:
                    return card

    company = _company_key(row.company)
    if not company:
        return None
    pool = [
        card
        for card in cards
        if not card.is_archived
        and _company_key(card.company) == company
        and card.status in ACTIVE_PIPELINE_STATUSES
    ]
    if not pool:
        pool = [
            card
            for card in cards
            if not card.is_archived and _company_key(card.company) == company
        ]
    if not pool:
        return None
    if len(pool) == 1:
        return pool[0]

    scored = sorted(
        pool,
        key=lambda card: _title_overlap(row.job_title, card.title),
        reverse=True,
    )
    best = scored[0]
    if _title_overlap(row.job_title, best.title) >= 0.4:
        return best
    return None


def plan_row_transition(
    row: HirifyApplicationRow,
    card: ProjectCard | None,
) -> tuple[str, str, str | None, str | None]:
    """Return (action, new_status, close_reason, closed_stage).

    action: create | update | note | noop
    """
    plan = map_hirify_stage(row.stage)

    if card is None:
        if plan.note_only:
            return "create", "Applied", None, None
        if plan.status == "Archived":
            closed = "Applied"
            return "create", "Archived", plan.close_reason, closed
        return "create", plan.status or "Applied", plan.close_reason, plan.closed_stage

    current = card.status

    if plan.note_only:
        return "note", current, None, None

    if plan.status == "Archived" and plan.close_reason:
        if current in ACTIVE_PIPELINE_STATUSES:
            closed_stage = current
            return "update", "Archived", plan.close_reason, closed_stage
        return "noop", current, None, None

    target = plan.status or current
    if target == current:
        return "noop", current, None, None
    if current == "Archived":
        return "noop", current, None, None
    if _rank(target) > _rank(current):
        return "update", target, None, None
    return "noop", current, None, None


def _recruiter_name(row: HirifyApplicationRow) -> str:
    contact = (row.recruiter_contact or "").strip()
    if not contact:
        return ""
    if contact.lower().startswith(("http://", "https://")):
        return ""
    return contact[:200]


def _sync_note(row: HirifyApplicationRow, *, today: date, new_status: str) -> str:
    parts = [
        f"{today.isoformat()}: hirify sync → {new_status} (stage={row.stage or '?'})",
    ]
    if row.job_url:
        parts.append(f"Hirify Job URL: {row.job_url}")
    if row.comment:
        parts.append(f"Comment: {row.comment}")
    if row.feedback:
        parts.append(f"Feedback: {row.feedback}")
    return "\n".join(parts)


def _manual_card_from_row(
    row: HirifyApplicationRow,
    *,
    status: str,
    close_reason: str | None,
    closed_stage: str | None,
    notes: str,
    follow_up: str | None = None,
) -> ManualCard:
    applied = row.date_applied.isoformat() if row.date_applied else None
    return ManualCard(
        company=row.company or "Unknown",
        title=row.job_title or "Role",
        status=status,
        source="hirify.me",
        channel="Other",
        recruiter=_recruiter_name(row) or None,
        salary=(row.expected_salary or None),
        url=row.preferred_url or row.job_url,
        applied_at=applied,
        follow_up=follow_up,
        close_reason=close_reason,
        closed_stage=closed_stage,
        notes=notes,
        summary=(
            f"{row.work_type} via Hirify".strip()
            if row.work_type
            else "Tracked via Hirify Applications export."
        ),
    )


def apply_row(
    settings: Settings,
    row: HirifyApplicationRow,
    card: ProjectCard | None,
    *,
    dry_run: bool = False,
    client: GitHubClient | None = None,
    today: date | None = None,
) -> HirifySyncMutation:
    stamp = today or date.today()
    action, new_status, close_reason, closed_stage = plan_row_transition(row, card)

    if action == "noop":
        return HirifySyncMutation(
            row=row,
            card=card,
            action="noop",
            previous_status=card.status if card else "",
            new_status=card.status if card else "",
            item_id=card.item_id if card else "",
        )

    if dry_run:
        return HirifySyncMutation(
            row=row,
            card=card,
            action="would_create" if action == "create" else f"would_{action}",
            previous_status=card.status if card else "",
            new_status=new_status,
            item_id=card.item_id if card else "",
            created=action == "create",
        )

    note = _sync_note(row, today=stamp, new_status=new_status)
    if card and card.body:
        if note not in card.body:
            note = f"{card.body.rstrip()}\n\n{note}"

    follow_up = None
    if action == "note":
        follow_up = (stamp + timedelta(days=3)).isoformat()

    manual = _manual_card_from_row(
        row,
        status=new_status,
        close_reason=close_reason,
        closed_stage=closed_stage,
        notes=note,
        follow_up=follow_up,
    )
    if card and not manual.url:
        manual = ManualCard(
            company=manual.company,
            title=manual.title,
            status=manual.status,
            source=manual.source,
            channel=manual.channel,
            recruiter=manual.recruiter,
            salary=manual.salary,
            url=card.url or card.canonical_url,
            applied_at=manual.applied_at or (
                card.applied_at.isoformat() if card.applied_at else None
            ),
            follow_up=follow_up,
            close_reason=close_reason,
            closed_stage=closed_stage,
            notes=note,
            summary=manual.summary,
        )

    item_id, created = upsert_private_card(settings, manual, client=client)
    if new_status == "Archived" and card is not None:
        card.is_archived = True
    if created or action == "create":
        seed_seen_from_manual_card(manual)

    return HirifySyncMutation(
        row=row,
        card=card,
        action="created" if created or action == "create" else (
            "noted" if action == "note" else "updated"
        ),
        previous_status=card.status if card else "",
        new_status=new_status,
        item_id=item_id,
        created=created or action == "create",
    )


def run_hirify_sync(
    settings: Settings,
    *,
    xlsx_path: Path | str | None = None,
    dry_run: bool = False,
    hirify_seen_path: Path | None = None,
    rows: list[HirifyApplicationRow] | None = None,
    cards: list[ProjectCard] | None = None,
    client: GitHubClient | None = None,
    today: date | None = None,
) -> HirifySyncResult:
    path: Path | None
    if rows is None:
        if xlsx_path is None:
            path = latest_applications_xlsx()
        else:
            path = Path(xlsx_path)
        if path is None or not path.is_file():
            raise FileNotFoundError(
                "Hirify Excel export not found. Pass --xlsx PATH "
                "or export Applications to ~/Downloads/my_applications_*.xlsx"
            )
        parsed = parse_applications_xlsx(path)
        xlsx_label = str(path)
    else:
        parsed = rows
        xlsx_label = str(xlsx_path or "")

    seen_path = hirify_seen_path or default_hirify_seen_path()
    seen = load_hirify_seen(seen_path)
    result = HirifySyncResult(
        rows=len(parsed),
        dry_run=dry_run,
        mutations=[],
        xlsx_path=xlsx_label,
    )

    gh = client
    board_cards = cards
    if board_cards is None:
        gh = gh or GitHubClient(settings.github_token)
        board_cards = load_cards_from_github(gh, settings)
    elif not dry_run:
        gh = gh or GitHubClient(settings.github_token)

    changed_seen = False
    assert result.mutations is not None
    for row in parsed:
        fingerprint = row.fingerprint
        if is_processed(seen, fingerprint):
            result.skipped_seen += 1
            continue

        card = match_card(row, board_cards)
        mutation = apply_row(
            settings,
            row,
            card,
            dry_run=dry_run,
            client=gh,
            today=today,
        )
        result.mutations.append(mutation)

        if not dry_run:
            marked = mark_processed(
                seen,
                fingerprint,
                stage=row.stage,
                item_id=mutation.item_id or None,
                company=row.company,
                action=mutation.action,
            )
            changed_seen = changed_seen or marked
            if mutation.created and mutation.item_id:
                board_cards.append(
                    ProjectCard(
                        item_id=mutation.item_id,
                        issue_number=None,
                        title=f"{row.company} — {row.job_title}",
                        url=row.preferred_url or row.job_url,
                        issue_url="",
                        company=row.company,
                        source="hirify.me",
                        canonical_url=canonicalize_url(row.preferred_url or row.job_url),
                        status=mutation.new_status,
                        priority="",
                        offer_probability="",
                        follow_up=None,
                        applied_at=row.date_applied,
                        created_at=None,
                        updated_at=None,
                        body="",
                    )
                )

    if changed_seen and not dry_run:
        save_hirify_seen(seen_path, seen)
    return result
