from __future__ import annotations

from email.message import EmailMessage

import pytest

from integrations import email_smtp


def test_credentials_require_user_and_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    monkeypatch.delenv("REPORT_EMAIL_TO", raising=False)
    assert email_smtp.credentials_configured() is False
    assert email_smtp.report_email_to() == "vil4max@gmail.com"


def test_send_email_builds_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_USER", "vil4max@gmail.com")
    monkeypatch.setenv("SMTP_PASS", "app-pass")
    monkeypatch.setenv("REPORT_EMAIL_TO", "vil4max@gmail.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")

    captured: dict = {}

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int = 30) -> None:
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def ehlo(self) -> None:
            captured.setdefault("ehlo", 0)
            captured["ehlo"] += 1

        def starttls(self, *, context=None) -> None:
            captured["starttls"] = True

        def login(self, user: str, password: str) -> None:
            captured["login"] = (user, password)

        def send_message(self, message: EmailMessage) -> None:
            captured["message"] = message

    monkeypatch.setattr(email_smtp.smtplib, "SMTP", FakeSMTP)

    email_smtp.send_email(subject="Career Agent · 2026-07-29", body="hello")

    assert captured["host"] == "smtp.example.com"
    assert captured["port"] == 587
    assert captured["login"] == ("vil4max@gmail.com", "app-pass")
    assert captured["starttls"] is True
    message = captured["message"]
    assert message["Subject"] == "Career Agent · 2026-07-29"
    assert message["To"] == "vil4max@gmail.com"
    assert message["From"] == "vil4max@gmail.com"
    assert message.get_content().strip() == "hello"


def test_send_email_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    with pytest.raises(RuntimeError, match="SMTP not configured"):
        email_smtp.send_email(subject="x", body="y")
