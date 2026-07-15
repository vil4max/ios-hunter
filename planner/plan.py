from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from config.settings import (
    ACTIVE_PIPELINE_STATUSES,
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
        if self.company and self.title:
            return f"{self.company} — {self.title}"
        return self.title or self.company or self.canonical_url or self.issue_url


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
    title = str(content.get("title") or "")
    company = fields.get("Company", "")
    if " — " in title and not company:
        company, _, rest = title.partition(" — ")
        if rest:
            title = rest

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
        if card.status == "Archived":
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
        elif card.status in {"Technical", "Screening"} and card.follow_up and follow_upcoming:
            plan.upcoming_interviews.append(card)
            ranked.append((1, card))
        elif card.status in STALE_STATUSES and age is not None and age >= settings.stale_days:
            plan.needs_attention.append(card)
            ranked.append((2, card))
        elif card.status == "Inbox" and (age is None or age <= settings.inbox_new_days):
            plan.new_vacancies.append(card)
            ranked.append((3, card))
        elif card.status == "Inbox":
            ranked.append((4, card))
        elif card.status == "Applied":
            ranked.append((5, card))
        elif card.status in ACTIVE_PIPELINE_STATUSES:
            ranked.append((6, card))

        if follow_upcoming and card not in plan.upcoming_interviews:
            plan.upcoming_interviews.append(card)

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
