from __future__ import annotations

from email.message import EmailMessage

import pytest

from integrations import email_imap
from integrations.email_imap import extract_body_text, parse_message


def test_imap_credentials_reuse_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    assert email_imap.credentials_configured() is False
    monkeypatch.setenv("SMTP_USER", "vil4max@gmail.com")
    monkeypatch.setenv("SMTP_PASS", "app-pass")
    assert email_imap.credentials_configured() is True
    assert email_imap.imap_host() == "imap.gmail.com"
    assert email_imap.imap_port() == 993
    assert email_imap.imap_folder() == "[Gmail]/All Mail"


def test_smtp_pass_strips_app_password_spaces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_PASS", " abcd efgh ijkl mnop \n")
    assert email_imap.smtp_password() == "abcdefghijklmnop"


def test_fetch_auth_failure_raises_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_USER", "vil4max@gmail.com")
    monkeypatch.setenv("SMTP_PASS", "bad-pass")
    monkeypatch.setattr(email_imap.time, "sleep", lambda _seconds: None)

    class FakeIMAP:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def login(self, user: str, password: str) -> None:
            raise email_imap.imaplib.IMAP4.error(
                b"[AUTHENTICATIONFAILED] Invalid credentials (Failure)"
            )

        def logout(self) -> None:
            return None

    monkeypatch.setattr(email_imap.imaplib, "IMAP4_SSL", FakeIMAP)

    with pytest.raises(RuntimeError, match="Gmail IMAP authentication failed"):
        email_imap.fetch_recent_mail(login_attempts=2)


def test_quote_mailbox_gmail_all_mail() -> None:
    assert email_imap.quote_mailbox("[Gmail]/All Mail") == '"[Gmail]/All Mail"'
    assert email_imap.quote_mailbox("INBOX") == "INBOX"
    assert email_imap.quote_mailbox('"[Gmail]/All Mail"') == '"[Gmail]/All Mail"'


def test_parse_message_plain() -> None:
    message = EmailMessage()
    message["Message-ID"] = "<ack@welltech.com>"
    message["Subject"] = "Thanks for Applying to Welltech!"
    message["From"] = "Welltech Recruitment Team <recruiting@welltech.com>"
    message["Date"] = "Wed, 29 Jul 2026 15:19:00 +0300"
    message.set_content("Dear Max,\n\nThanks for applying to Welltech!\n")

    mail = parse_message(message.as_bytes())
    assert mail is not None
    assert mail.message_id == "<ack@welltech.com>"
    assert mail.from_addr == "recruiting@welltech.com"
    assert "Thanks for applying" in mail.body_text
    assert mail.subject.startswith("Thanks for Applying")


def test_extract_body_prefers_plain_over_html() -> None:
    message = EmailMessage()
    message["Message-ID"] = "<x@y.com>"
    message.set_content("plain body")
    message.add_alternative("<p>html body</p>", subtype="html")
    assert extract_body_text(message) == "plain body"


def test_parse_message_requires_message_id() -> None:
    message = EmailMessage()
    message["Subject"] = "No id"
    message.set_content("hi")
    assert parse_message(message.as_bytes()) is None
