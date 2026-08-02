from __future__ import annotations

from integrations.mail_classify import (
    KIND_APPLICATION_ACK,
    KIND_IGNORE,
    KIND_REJECTED_HR,
    KIND_REPLIED,
    KIND_SCREENING,
    classify_from_headers,
)


def test_classify_welltech_ack() -> None:
    event = classify_from_headers(
        message_id="<1@welltech.com>",
        subject="Thanks for Applying to Welltech!",
        from_header="Welltech Recruitment Team <recruiting@welltech.com>",
        body_text="Dear Max,\n\nThanks for applying to Welltech! We received your application.\n",
    )
    assert event.kind == KIND_APPLICATION_ACK
    assert event.company == "Welltech"


def test_classify_welltech_via_ashby_ses() -> None:
    event = classify_from_headers(
        message_id="<0100019fadd13d4f-b8c430b5@email.amazonses.com>",
        subject="Thanks for Applying to Welltech!",
        from_header="Welltech <jobs@ashbyhq.com>",
        body_text="Dear Max,\n\nThanks for applying to Welltech!\n",
    )
    assert event.kind == KIND_APPLICATION_ACK
    assert event.company == "Welltech"


def test_classify_nix_ack() -> None:
    event = classify_from_headers(
        message_id="<2@n-ix.com>",
        subject="Thank you for your application!",
        from_header="Recruitment Team <recruitmentteam@n-ix.com>",
        body_text=(
            "Dear Max,\nThank you for your interest in N-iX!\n"
            "APPLICATION RECEIVED for the Senior Mobile/Web Engineer position.\n"
        ),
    )
    assert event.kind == KIND_APPLICATION_ACK
    assert event.company == "N-iX"
    assert "Mobile" in event.role_hint or "Engineer" in event.role_hint


def test_classify_reject() -> None:
    event = classify_from_headers(
        message_id="<3@acme.com>",
        subject="Update on your application",
        from_header="HR <jobs@acme.io>",
        body_text=(
            "Unfortunately we will not be moving forward with other candidates "
            "at this time."
        ),
    )
    assert event.kind == KIND_REJECTED_HR


def test_classify_screening() -> None:
    event = classify_from_headers(
        message_id="<4@softserve.com>",
        subject="Interview invitation — SoftServe",
        from_header="Anna Recruiter <anna@softserve.com>",
        body_text="Hi Max, can we schedule a call for a screening interview next week?",
    )
    assert event.kind == KIND_SCREENING
    assert event.company == "SoftServe"
    assert event.recruiter.startswith("Anna")


def test_classify_recruiter_reply() -> None:
    event = classify_from_headers(
        message_id="<5@lineup.software>",
        subject="Your LineUp application",
        from_header="HR Team <careers@lineup.software>",
        body_text="Hi Max, thanks for reaching out — we reviewed your CV and have a few questions.",
    )
    assert event.kind == KIND_REPLIED
    assert event.company == "LineUp"


def test_classify_noise_newsletter() -> None:
    event = classify_from_headers(
        message_id="<6@linkedin.com>",
        subject="Jobs you may like",
        from_header="LinkedIn <jobs-noreply@linkedin.com>",
        body_text="Here are new jobs based on your preferences.",
    )
    assert event.kind == KIND_IGNORE


def test_classify_ignores_uber_two_step_auth() -> None:
    event = classify_from_headers(
        message_id="<33a9a92e-0d33-42fe-9c72-a3647cff8c69@mail.uber.com>",
        subject="Максим, вы включили двухэтапную аутентификацию",
        from_header="Uber <uber@mail.uber.com>",
        body_text=(
            "Максим, вы включили двухэтапную аутентификацию в аккаунте Uber. "
            "Если это были не вы, свяжитесь с нами. "
            "More: https://www.uber.com/us/en/careers/recruiting/"
        ),
    )
    assert event.kind == KIND_IGNORE
    assert event.company == "Uber"


def test_classify_ignores_english_two_factor_security_mail() -> None:
    event = classify_from_headers(
        message_id="<tf@accounts.example.com>",
        subject="Two-factor authentication turned on",
        from_header="Example Security <security@example.com>",
        body_text="You turned on two-factor authentication for your account.",
    )
    assert event.kind == KIND_IGNORE
