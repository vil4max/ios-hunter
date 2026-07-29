from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage


def smtp_host() -> str:
    return os.environ.get("SMTP_HOST", "").strip() or "smtp.gmail.com"


def smtp_port() -> int:
    raw = os.environ.get("SMTP_PORT", "").strip()
    if not raw:
        return 587
    try:
        return int(raw)
    except ValueError:
        return 587


def smtp_user() -> str:
    return os.environ.get("SMTP_USER", "").strip()


def smtp_password() -> str:
    return os.environ.get("SMTP_PASS", "").strip()


def smtp_from() -> str:
    return os.environ.get("SMTP_FROM", "").strip() or smtp_user()


def report_email_to() -> str:
    return os.environ.get("REPORT_EMAIL_TO", "").strip() or "vil4max@gmail.com"


def credentials_configured() -> bool:
    return bool(smtp_user() and smtp_password() and report_email_to())


def send_email(*, subject: str, body: str, to: str | None = None) -> None:
    if not credentials_configured():
        raise RuntimeError(
            "SMTP not configured (need SMTP_USER, SMTP_PASS; optional REPORT_EMAIL_TO)"
        )

    recipient = (to or report_email_to()).strip()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_from()
    message["To"] = recipient
    message.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host(), smtp_port(), timeout=30) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(smtp_user(), smtp_password())
        server.send_message(message)
