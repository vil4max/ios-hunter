from __future__ import annotations

import email
import email.header
import email.utils
import imaplib
import os
import re
import time
from dataclasses import dataclass
from email.message import Message
from typing import Iterable

from integrations.email_smtp import smtp_password, smtp_user

_AUTH_HINT = (
    "Gmail IMAP authentication failed. Regenerate a Gmail App Password at "
    "https://myaccount.google.com/apppasswords and update the SMTP_PASS "
    "repository secret (16 characters; spaces are ignored)."
)


def imap_host() -> str:
    return os.environ.get("IMAP_HOST", "").strip() or "imap.gmail.com"


def imap_port() -> int:
    raw = os.environ.get("IMAP_PORT", "").strip()
    if not raw:
        return 993
    try:
        return int(raw)
    except ValueError:
        return 993


def imap_folder() -> str:
    return os.environ.get("IMAP_FOLDER", "").strip() or "[Gmail]/All Mail"


def quote_mailbox(name: str) -> str:
    folder = (name or "").strip() or "[Gmail]/All Mail"
    if folder.startswith('"') and folder.endswith('"'):
        return folder
    if re.search(r'[\s\[\]]', folder) or '"' in folder:
        escaped = folder.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return folder


def credentials_configured() -> bool:
    return bool(smtp_user() and smtp_password())


@dataclass(frozen=True)
class InboundMail:
    message_id: str
    subject: str
    from_addr: str
    from_name: str
    date: str
    body_text: str
    uid: str = ""


def _decode_header(raw: str | None) -> str:
    if not raw:
        return ""
    parts: list[str] = []
    for chunk, charset in email.header.decode_header(raw):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(str(chunk))
    return " ".join(parts).strip()


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def extract_body_text(message: Message) -> str:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    if message.is_multipart():
        for part in message.walk():
            content_type = (part.get_content_type() or "").lower()
            disposition = str(part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            payload = part.get_payload(decode=True)
            if not isinstance(payload, bytes):
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if content_type == "text/plain":
                plain_parts.append(text)
            elif content_type == "text/html":
                html_parts.append(text)
    else:
        payload = message.get_payload(decode=True)
        if isinstance(payload, bytes):
            charset = message.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if (message.get_content_type() or "").lower() == "text/html":
                html_parts.append(text)
            else:
                plain_parts.append(text)
    if plain_parts:
        return "\n".join(plain_parts).strip()
    if html_parts:
        return _strip_html("\n".join(html_parts))
    return ""


def parse_message(raw: bytes | Message, *, uid: str = "") -> InboundMail | None:
    message = raw if isinstance(raw, Message) else email.message_from_bytes(raw)
    message_id = (message.get("Message-ID") or message.get("Message-Id") or "").strip()
    if not message_id:
        return None
    from_raw = message.get("From") or ""
    name, addr = email.utils.parseaddr(from_raw)
    return InboundMail(
        message_id=message_id,
        subject=_decode_header(message.get("Subject")),
        from_addr=(addr or "").strip().lower(),
        from_name=_decode_header(name) or (addr or "").split("@", 1)[0],
        date=_decode_header(message.get("Date")),
        body_text=extract_body_text(message),
        uid=uid,
    )


def _search_uids(client: imaplib.IMAP4_SSL, criteria: str) -> list[str]:
    status, data = client.search(None, criteria)
    if status != "OK" or not data or not data[0]:
        return []
    return [uid.decode("ascii") if isinstance(uid, bytes) else str(uid) for uid in data[0].split()]


def _is_auth_failure(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "authenticationfailed" in text or "invalid credentials" in text


def _fetch_with_client(
    connection: imaplib.IMAP4_SSL,
    *,
    limit: int,
    since_days: int,
) -> list[InboundMail]:
    folder = imap_folder()
    status, _ = connection.select(quote_mailbox(folder), readonly=True)
    if status != "OK":
        raise RuntimeError(f"IMAP select failed for folder {folder!r}")

    uids = _search_uids(connection, f"(SINCE {_imap_since_date(since_days)})")
    if not uids:
        uids = _search_uids(connection, "ALL")
    if limit > 0:
        uids = uids[-limit:]

    mails: list[InboundMail] = []
    for uid in uids:
        status, data = connection.fetch(uid, "(RFC822)")
        if status != "OK" or not data:
            continue
        raw = None
        for item in data:
            if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
                raw = item[1]
                break
        if raw is None:
            continue
        parsed = parse_message(raw, uid=uid)
        if parsed:
            mails.append(parsed)
    return mails


def fetch_recent_mail(
    *,
    limit: int = 40,
    since_days: int = 7,
    client: imaplib.IMAP4_SSL | None = None,
    login_attempts: int = 3,
) -> list[InboundMail]:
    if not credentials_configured():
        raise RuntimeError("IMAP not configured (need SMTP_USER + SMTP_PASS)")

    if client is not None:
        return _fetch_with_client(client, limit=limit, since_days=since_days)

    attempts = max(1, login_attempts)
    last_error: BaseException | None = None
    for attempt in range(attempts):
        connection = imaplib.IMAP4_SSL(imap_host(), imap_port())
        try:
            connection.login(smtp_user(), smtp_password())
            return _fetch_with_client(connection, limit=limit, since_days=since_days)
        except imaplib.IMAP4.error as exc:
            last_error = exc
            if _is_auth_failure(exc) and attempt + 1 < attempts:
                time.sleep(2**attempt)
                continue
            if _is_auth_failure(exc):
                raise RuntimeError(_AUTH_HINT) from exc
            raise
        finally:
            try:
                connection.logout()
            except Exception:
                pass
    assert last_error is not None
    raise RuntimeError(_AUTH_HINT) from last_error


def _imap_since_date(since_days: int) -> str:
    from datetime import datetime, timedelta, timezone

    days = max(1, since_days)
    stamp = datetime.now(timezone.utc) - timedelta(days=days)
    return stamp.strftime("%d-%b-%Y")


def iter_unprocessed(
    mails: Iterable[InboundMail],
    processed_ids: set[str],
) -> list[InboundMail]:
    result: list[InboundMail] = []
    for mail in mails:
        if mail.message_id in processed_ids:
            continue
        result.append(mail)
    return result
