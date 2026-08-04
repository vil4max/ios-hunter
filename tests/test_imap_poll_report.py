from __future__ import annotations

from datetime import datetime, timezone

from integrations.mail_classify import (
    KIND_APPLICATION_ACK,
    KIND_REJECTED_HR,
    KIND_REPLIED,
    KIND_SCREENING,
    MailEvent,
)
from planner.plan import ProjectCard
from project_sync.mail_sync import MailSyncMutation, MailSyncResult
from reporter.imap_poll import format_imap_poll_message


def _event(kind: str, *, company: str, subject: str, role: str = "") -> MailEvent:
    return MailEvent(
        kind=kind,
        company=company,
        role_hint=role,
        recruiter="",
        confidence=0.8,
        snippet="",
        subject=subject,
        from_addr="hr@example.com",
        message_id="<x>",
    )


def _card(company: str, title: str, status: str) -> ProjectCard:
    now = datetime(2026, 7, 29, tzinfo=timezone.utc)
    return ProjectCard(
        item_id="1",
        issue_number=None,
        title=title,
        url="https://example.com",
        issue_url="",
        company=company,
        source="",
        canonical_url="https://example.com",
        status=status,
        priority="",
        offer_probability="",
        follow_up=None,
        applied_at=None,
        created_at=now,
        updated_at=now,
        body="",
    )


def test_format_groups_matched_board_updates_only() -> None:
    result = MailSyncResult(
        mutations=[
            MailSyncMutation(
                event=_event(
                    KIND_REPLIED,
                    company="BetterMe",
                    subject="Hiring Team Re: Senior iOS Engineer | Portfolio",
                    role="Senior iOS Engineer",
                ),
                card=None,
                action="unmatched",
                previous_status="",
                new_status="",
                unmatched=True,
            ),
            MailSyncMutation(
                event=_event(
                    KIND_APPLICATION_ACK,
                    company="Northstrat",
                    subject="Thanks for applying to Northstrat",
                ),
                card=None,
                action="unmatched",
                previous_status="",
                new_status="",
                unmatched=True,
            ),
            MailSyncMutation(
                event=_event(
                    KIND_REJECTED_HR,
                    company="Acme",
                    subject="Update on your application",
                ),
                card=_card("Acme", "iOS Engineer", "Applied"),
                action="updated",
                previous_status="Applied",
                new_status="Archived",
                item_id="1",
            ),
            MailSyncMutation(
                event=_event(
                    KIND_SCREENING,
                    company="SoftServe",
                    subject="Interview invitation",
                ),
                card=_card("SoftServe", "Senior iOS", "Screening"),
                action="noop",
                previous_status="Screening",
                new_status="Screening",
                item_id="2",
            ),
        ]
    )
    text = format_imap_poll_message(
        result,
        board_url="https://github.com/users/vil4max/projects/3",
    )
    assert text is not None
    assert "https://github.com" not in text
    assert text.startswith("📬 Почта")
    assert "❌ Отказ HR" in text
    assert "📅 Screening / interview" in text
    assert "CRM: Applied → Archived" in text
    assert "уже на борде: Screening" in text
    assert "BetterMe" not in text
    assert "Northstrat" not in text
    assert "⚠ нет карточки на борде" not in text
    assert "💬 Reply от рекрутера" not in text
    assert "🤖 Автоответ (заявка принята)" not in text


def test_format_returns_none_when_only_unmatched() -> None:
    result = MailSyncResult(
        mutations=[
            MailSyncMutation(
                event=_event(KIND_REJECTED_HR, company="FOP_CREDIT", subject="Кредит"),
                card=None,
                action="unmatched",
                previous_status="",
                new_status="",
                unmatched=True,
            )
        ]
    )
    assert format_imap_poll_message(result) is None
