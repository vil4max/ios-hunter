from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from config.settings import Settings
from integrations.email_imap import InboundMail
from integrations.mail_classify import (
    KIND_APPLICATION_ACK,
    KIND_REJECTED_HR,
    KIND_REPLIED,
    KIND_SCREENING,
    MailEvent,
)
from planner.plan import ProjectCard
from project_sync.mail_sync import (
    match_card,
    plan_transition,
    process_mail_event,
    run_mail_sync,
)


def _settings() -> Settings:
    return Settings(
        github_token="token",
        github_repository="vil4max/ios-hunter",
        project_owner="vil4max",
        project_number=3,
        project_board_url="https://github.com/users/vil4max/projects/3",
        sync_enabled=True,
        seen_gate_enabled=False,
        stale_days=7,
        inbox_new_days=2,
        research_stale_days=5,
    )


def _card(
    *,
    item_id: str,
    company: str,
    title: str,
    status: str,
    url: str = "https://example.com/job",
) -> ProjectCard:
    now = datetime(2026, 7, 29, tzinfo=timezone.utc)
    return ProjectCard(
        item_id=item_id,
        issue_number=None,
        title=title,
        url=url,
        issue_url="",
        company=company,
        source="dou",
        canonical_url=url,
        status=status,
        priority="",
        offer_probability="",
        follow_up=None,
        applied_at=None,
        created_at=now,
        updated_at=now,
        body="body",
    )


def _event(
    kind: str,
    *,
    company: str,
    role_hint: str = "",
    message_id: str = "<m@x>",
    confidence: float = 0.8,
) -> MailEvent:
    return MailEvent(
        kind=kind,
        company=company,
        role_hint=role_hint,
        recruiter="",
        confidence=confidence,
        snippet="snippet",
        subject="subj",
        from_addr="hr@example.com",
        message_id=message_id,
    )


def test_plan_transition_matrix() -> None:
    applied = _card(item_id="1", company="Welltech", title="Senior", status="Applied")
    assert plan_transition(_event(KIND_APPLICATION_ACK, company="Welltech"), applied)[0] == "noop"
    assert plan_transition(_event(KIND_REPLIED, company="Welltech"), applied)[1] == "Replied"

    inbox = _card(item_id="2", company="Welltech", title="Senior", status="Inbox")
    assert plan_transition(_event(KIND_APPLICATION_ACK, company="Welltech"), inbox)[1] == "Applied"

    interview = _card(item_id="3", company="Welltech", title="Senior", status="Interview")
    assert plan_transition(_event(KIND_REPLIED, company="Welltech"), interview)[0] == "noop"
    assert plan_transition(_event(KIND_SCREENING, company="Welltech"), interview)[0] == "noop"

    action, status, reason, stage = plan_transition(
        _event(KIND_REJECTED_HR, company="Welltech", confidence=0.95),
        applied,
    )
    assert action == "update"
    assert status == "Archived"
    assert reason == "Rejected HR"
    assert stage == "Applied"


def test_low_confidence_rejection_does_not_archive() -> None:
    applied = _card(item_id="1", company="Welltech", title="Senior", status="Applied")

    action, status, reason, stage = plan_transition(
        _event(KIND_REJECTED_HR, company="Welltech", confidence=0.7),
        applied,
    )

    assert action == "noop"
    assert status == "Applied"
    assert reason is None
    assert stage is None


def test_nix_and_n_ix_are_not_company_aliases() -> None:
    cards = [
        _card(item_id="nix", company="NIX", title="Middle iOS Developer", status="Applied"),
        _card(item_id="n-ix", company="N-iX", title="Middle iOS Engineer", status="Applied"),
    ]

    assert match_card(_event(KIND_APPLICATION_ACK, company="NIX"), cards).item_id == "nix"
    assert match_card(_event(KIND_APPLICATION_ACK, company="N-iX"), cards).item_id == "n-ix"


def test_match_card_by_company_and_role() -> None:
    cards = [
        _card(item_id="a", company="N-iX", title="Lead iOS Engineer", status="Applied"),
        _card(
            item_id="b",
            company="N-iX",
            title="Senior Mobile/Web Engineer",
            status="Applied",
        ),
    ]
    event = _event(
        KIND_APPLICATION_ACK,
        company="N-iX",
        role_hint="Senior Mobile/Web Engineer",
    )
    matched = match_card(event, cards)
    assert matched is not None
    assert matched.item_id == "b"


def test_match_card_ignores_project_archived_items() -> None:
    archived = _card(item_id="old", company="N-iX", title="Senior iOS", status="Applied")
    archived.is_archived = True

    assert match_card(_event(KIND_REPLIED, company="N-iX"), [archived]) is None


def test_process_unmatched() -> None:
    mutation = process_mail_event(
        _settings(),
        _event(KIND_REPLIED, company="UnknownCo"),
        [],
        dry_run=True,
    )
    assert mutation.unmatched is True
    assert mutation.action == "unmatched"


def test_run_mail_sync_dry_run_marks_nothing(tmp_path: Path) -> None:
    seen_path = tmp_path / "email_seen.json"
    mail = InboundMail(
        message_id="<ack@welltech.com>",
        subject="Thanks for Applying to Welltech!",
        from_addr="recruiting@welltech.com",
        from_name="Welltech Recruitment",
        date="",
        body_text="Thanks for applying to Welltech! Application received.",
    )
    cards = [
        _card(
            item_id="w1",
            company="Welltech",
            title="Senior Fullstack Engineer, Cross-platform",
            status="Inbox",
        )
    ]
    result = run_mail_sync(
        _settings(),
        dry_run=True,
        email_seen_path=seen_path,
        mails=[mail],
        cards=cards,
    )
    assert result.fetched == 1
    assert result.mutations
    assert result.mutations[0].action == "would_update"
    assert result.mutations[0].new_status == "Applied"
    assert not seen_path.exists()
