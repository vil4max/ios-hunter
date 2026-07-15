from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from config.settings import (
    STALE_STATUSES,
    Settings,
    STATUS_WORKFLOW,
)
from project_sync.github_client import GitHubClient


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _split_company_title(title: str, company: str) -> tuple[str, str]:
    """Normalize draft titles like 'Acme — Role' so display is not doubled."""
    raw_title = (title or "").strip()
    raw_company = (company or "").strip()
    if " — " in raw_title:
        left, _, right = raw_title.partition(" — ")
        left, right = left.strip(), right.strip()
        if right:
            if not raw_company:
                raw_company = left
            elif left.lower() == raw_company.lower() or raw_title.lower().startswith(
                (raw_company + " — ").lower()
            ):
                raw_title = right
            else:
                raw_title = right
    if raw_company and raw_title.lower().startswith((raw_company + " — ").lower()):
        raw_title = raw_title[len(raw_company) + 3 :].strip()
    return raw_company, raw_title


@dataclass
class ProjectCard:
    item_id: str
    issue_number: int | None
    title: str
    url: str
    issue_url: str
    company: str
    source: str
    canonical_url: str
    status: str
    priority: str
    offer_probability: str
    follow_up: date | None
    applied_at: date | None
    created_at: datetime | None
    updated_at: datetime | None
    body: str = ""

    @property
    def display_title(self) -> str:
        company, title = _split_company_title(self.title, self.company)
        if company and title:
            return f"{company} — {title}"
        return title or company or self.canonical_url or self.issue_url


def parse_project_item(raw: dict[str, Any]) -> ProjectCard | None:
    content = raw.get("content")
    if not isinstance(content, dict):
        return None
    if content.get("state") == "CLOSED":
        return None

    fields: dict[str, str] = {}
    for node in (raw.get("fieldValues") or {}).get("nodes") or []:
        if not isinstance(node, dict):
            continue
        field_meta = node.get("field") or {}
        name = field_meta.get("name")
        if not name:
            continue
        if "text" in node and node["text"] is not None:
            fields[str(name)] = str(node["text"])
        elif "name" in node and node["name"] is not None and "date" not in node:
            fields[str(name)] = str(node["name"])
        elif "date" in node and node["date"] is not None:
            fields[str(name)] = str(node["date"])

    status = fields.get("Status", "Inbox")
    company, title = _split_company_title(
        str(content.get("title") or ""),
        fields.get("Company", ""),
    )

    updated = _parse_datetime(str(raw.get("updatedAt") or content.get("updatedAt") or ""))
    created = _parse_datetime(str(content.get("createdAt") or ""))

    return ProjectCard(
        item_id=str(raw.get("id") or ""),
        issue_number=int(content["number"]) if content.get("number") is not None else None,
        title=title,
        url=fields.get("URL") or str(content.get("url") or ""),
        issue_url=str(content.get("url") or ""),
        company=company,
        source=fields.get("Source", ""),
        canonical_url=fields.get("Canonical URL", ""),
        status=status,
        priority=fields.get("Priority", ""),
        offer_probability=fields.get("Offer Probability", ""),
        follow_up=_parse_date(fields.get("Follow Up")),
        applied_at=_parse_date(fields.get("Applied At")),
        created_at=created,
        updated_at=updated,
        body=str(content.get("body") or ""),
    )


@dataclass
class DailyPlan:
    today_tasks: list[ProjectCard] = field(default_factory=list)
    new_vacancies: list[ProjectCard] = field(default_factory=list)
    needs_attention: list[ProjectCard] = field(default_factory=list)
    pending_follow_ups: list[ProjectCard] = field(default_factory=list)
    upcoming_interviews: list[ProjectCard] = field(default_factory=list)
    status_counts: dict[str, int] = field(default_factory=dict)
    cards: list[ProjectCard] = field(default_factory=list)


def _age_days(card: ProjectCard, today: date) -> int | None:
    stamp = card.updated_at or card.created_at
    if stamp is None and card.applied_at is not None:
        return (today - card.applied_at).days
    if stamp is None:
        return None
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(timezone.utc).replace(tzinfo=None)
    return (today - stamp.date()).days


def build_plan(cards: list[ProjectCard], settings: Settings, *, today: date | None = None) -> DailyPlan:
    today = today or date.today()
    plan = DailyPlan(cards=list(cards))
    status_counts = {name: 0 for name in STATUS_WORKFLOW}
    for card in cards:
        status_counts[card.status] = status_counts.get(card.status, 0) + 1
    plan.status_counts = status_counts

    ranked: list[tuple[int, ProjectCard]] = []
    for card in cards:
        if card.status in {"Archived", "Rejected", "Offer"}:
            continue

        age = _age_days(card, today)
        follow_due = card.follow_up is not None and card.follow_up <= today
        follow_upcoming = (
            card.follow_up is not None
            and today < card.follow_up <= date.fromordinal(today.toordinal() + 7)
        )

        if follow_due:
            plan.pending_follow_ups.append(card)
            ranked.append((0, card))
            continue

        if card.status in {"Technical", "Screening"} and follow_upcoming:
            plan.upcoming_interviews.append(card)
            continue

        if card.status in STALE_STATUSES and age is not None and age >= settings.stale_days:
            plan.needs_attention.append(card)
            ranked.append((1, card))
            continue

        if card.status == "Inbox":
            if age is None or age <= settings.inbox_new_days:
                plan.new_vacancies.append(card)
            ranked.append((2, card))
            continue

        if card.status == "Screening" and not follow_upcoming:
            ranked.append((3, card))

    seen_ids: set[str] = set()
    for _, card in sorted(ranked, key=lambda pair: (pair[0], pair[1].display_title.lower())):
        if card.item_id in seen_ids:
            continue
        seen_ids.add(card.item_id)
        plan.today_tasks.append(card)

    return plan


def load_cards_from_github(client: GitHubClient, settings: Settings) -> list[ProjectCard]:
    meta = client.resolve_project(settings.project_owner, settings.project_number)
    raw_items = client.list_project_items(meta.project_id)
    cards: list[ProjectCard] = []
    for raw in raw_items:
        card = parse_project_item(raw)
        if card is not None:
            cards.append(card)
    return cards
