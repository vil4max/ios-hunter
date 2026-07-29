from __future__ import annotations

import re
from dataclasses import dataclass
from email.utils import parseaddr

from integrations.email_imap import InboundMail


MailKind = str

KIND_APPLICATION_ACK = "application_ack"
KIND_REPLIED = "replied"
KIND_SCREENING = "screening"
KIND_REJECTED_HR = "rejected_hr"
KIND_IGNORE = "ignore"


_DOMAIN_COMPANY: dict[str, str] = {
    "welltech.com": "Welltech",
    "welltech.org": "Welltech",
    "n-ix.com": "N-iX",
    "nixsolutions.com": "NIX",
    "softserve.com": "SoftServe",
    "lineup.software": "LineUp",
    "lineup.com": "LineUp",
}

_ATS_DOMAINS = frozenset(
    {
        "ashbyhq.com",
        "greenhouse.io",
        "lever.co",
        "workable.com",
        "comeet.co",
        "comeet.com",
        "jobvite.com",
        "smartrecruiters.com",
        "recruitee.com",
        "personio.de",
        "amazonses.com",
        "email.amazonses.com",
    }
)

_SUBJECT_COMPANY = (
    (re.compile(r"\bwelltech\b", re.I), "Welltech"),
    (re.compile(r"\bn-?ix\b", re.I), "N-iX"),
    (re.compile(r"\blineup\b", re.I), "LineUp"),
    (re.compile(r"\bgrammarly\b", re.I), "Grammarly"),
    (re.compile(r"\bsoftserve\b", re.I), "SoftServe"),
    (re.compile(r"\bepam\b", re.I), "EPAM"),
    (re.compile(r"\bintellias\b", re.I), "Intellias"),
    (re.compile(r"\bciklum\b", re.I), "Ciklum"),
    (re.compile(r"\bgloballogic\b", re.I), "GlobalLogic"),
)

_REJECT_PATTERNS = (
    re.compile(r"unfortunately", re.I),
    re.compile(r"not\s+(be\s+)?(able\s+to\s+)?proceed", re.I),
    re.compile(r"will\s+not\s+be\s+moving\s+forward", re.I),
    re.compile(r"decided\s+to\s+(move|go)\s+forward\s+with\s+(other|another)", re.I),
    re.compile(r"other\s+candidates", re.I),
    re.compile(r"not\s+selected", re.I),
    re.compile(r"position\s+has\s+been\s+filled", re.I),
    re.compile(r"we\s+regret\s+to\s+inform", re.I),
    re.compile(r"\bвідмов", re.I),
    re.compile(r"на\s+жаль", re.I),
    re.compile(r"к\s+сожалению", re.I),
    re.compile(r"не\s+будем\s+продолжать", re.I),
    re.compile(r"не\s+продовж", re.I),
)

_SCREENING_PATTERNS = (
    re.compile(r"\bscreening\b", re.I),
    re.compile(r"\binterview\b", re.I),
    re.compile(r"schedule\s+(a\s+)?(call|meeting|chat|interview)", re.I),
    re.compile(r"book\s+(a\s+)?(call|slot|time)", re.I),
    re.compile(r"calendly\.com", re.I),
    re.compile(r"\btechnical\s+(interview|screen)", re.I),
    re.compile(r"\bспівбесід", re.I),
    re.compile(r"\bсобеседован", re.I),
    re.compile(r"\bзустріч", re.I),
)

_ACK_PATTERNS = (
    re.compile(r"thanks?\s+for\s+apply", re.I),
    re.compile(r"thank\s+you\s+for\s+(your\s+)?(application|interest|applying)", re.I),
    re.compile(r"application\s+(has\s+been\s+)?received", re.I),
    re.compile(r"we\s+have\s+received\s+your\s+application", re.I),
    re.compile(r"successfully\s+submitted", re.I),
    re.compile(r"дякуємо\s+за\s+(відгук|заявку|інтерес)", re.I),
    re.compile(r"заявк[ау]\s+отримано", re.I),
    re.compile(r"отклик\s+получен", re.I),
)

_RECRUITER_HINTS = (
    re.compile(r"recruit", re.I),
    re.compile(r"talent\s+acquisition", re.I),
    re.compile(r"\bhr\b", re.I),
    re.compile(r"hiring", re.I),
    re.compile(r"careers?@", re.I),
    re.compile(r"jobs?@", re.I),
)

_ROLE_STOP = {
    "your",
    "our",
    "the",
    "application",
    "interest",
    "applying",
    "position",
    "role",
    "vacancy",
    "opportunity",
}

_ROLE_FOR_POSITION = re.compile(
    r"(?:for the|position(?: of)?|role(?: of)?|vacancy)\s+"
    r"((?:Senior|Middle|Lead|Junior|Staff|Principal)\s+"
    r"[A-Za-z][A-Za-z0-9/+\- ]{2,60}?)(?:\s+position|\s+role|[.!,]|$)",
    re.I,
)

_ROLE_SENIORITY = re.compile(
    r"\b((?:Senior|Middle|Lead|Junior|Staff|Principal)\s+"
    r"[A-Za-z][A-Za-z0-9/+\- ]{2,60})",
    re.I,
)

_NOISE_FROM = (
    re.compile(r"noreply@", re.I),
    re.compile(r"no-reply@", re.I),
    re.compile(r"newsletter@", re.I),
    re.compile(r"notifications?@", re.I),
    re.compile(r"linkedin\.com", re.I),
    re.compile(r"facebookmail\.com", re.I),
)


@dataclass(frozen=True)
class MailEvent:
    kind: MailKind
    company: str
    role_hint: str
    recruiter: str
    confidence: float
    snippet: str
    subject: str
    from_addr: str
    message_id: str


def _blob(mail: InboundMail) -> str:
    return f"{mail.subject}\n{mail.from_name}\n{mail.from_addr}\n{mail.body_text[:4000]}"


def _snippet(mail: InboundMail, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", mail.body_text or mail.subject).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _domain(addr: str) -> str:
    if "@" not in addr:
        return ""
    return addr.rsplit("@", 1)[-1].lower().strip()


def extract_company(mail: InboundMail) -> str:
    hay = f"{mail.subject}\n{mail.from_name}\n{mail.body_text[:1500]}"
    for pattern, company in _SUBJECT_COMPANY:
        if pattern.search(hay):
            return company

    domain = _domain(mail.from_addr)
    if domain in _DOMAIN_COMPANY:
        return _DOMAIN_COMPANY[domain]
    parts = domain.split(".")
    if len(parts) >= 3:
        parent = ".".join(parts[-2:])
        if parent in _DOMAIN_COMPANY:
            return _DOMAIN_COMPANY[parent]

    name = (mail.from_name or "").strip()
    if name and not re.search(r"recruit|talent|hr team|careers|noreply|no-reply", name, re.I):
        cleaned = re.sub(r"\s*(recruitment|talent|hr|team)\s*$", "", name, flags=re.I).strip()
        if cleaned and len(cleaned) <= 40:
            return cleaned

    if any(domain == ats or domain.endswith("." + ats) for ats in _ATS_DOMAINS):
        return ""

    if domain and domain not in {"gmail.com", "googlemail.com", "outlook.com", "yahoo.com"}:
        label = parts[0] if parts else domain
        if label and label not in {"mail", "email", "jobs", "careers", "noreply", "no-reply"}:
            return label.replace("-", " ").title()
    return ""


def _clean_role(raw: str) -> str:
    role = re.sub(r"\s+", " ", (raw or "").strip(" -–,."))
    if not (3 <= len(role) <= 80):
        return ""
    tokens = [t for t in role.split() if t.lower() not in _ROLE_STOP]
    if len(tokens) < 2:
        return ""
    return " ".join(tokens)


def extract_role_hint(mail: InboundMail) -> str:
    hay = f"{mail.body_text[:2000]}\n{mail.subject}"
    for pattern in (_ROLE_FOR_POSITION, _ROLE_SENIORITY):
        match = pattern.search(hay)
        if not match:
            continue
        role = _clean_role(match.group(1))
        if role:
            return role
    return ""


def extract_recruiter(mail: InboundMail) -> str:
    name = (mail.from_name or "").strip()
    if name and not re.search(r"recruitment|talent acquisition|noreply|no-reply", name, re.I):
        if " " in name or re.match(r"^[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ'’-]+$", name):
            return name[:80]
    return ""


def _matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _looks_recruiter_mail(mail: InboundMail) -> bool:
    hay = _blob(mail)
    if _matches_any(hay, _RECRUITER_HINTS):
        return True
    if _matches_any(hay, _ACK_PATTERNS + _REJECT_PATTERNS + _SCREENING_PATTERNS):
        return True
    domain = _domain(mail.from_addr)
    if domain in _DOMAIN_COMPANY:
        return True
    return False


def classify_mail(mail: InboundMail) -> MailEvent:
    hay = _blob(mail)
    company = extract_company(mail)
    role_hint = extract_role_hint(mail)
    recruiter = extract_recruiter(mail)
    snippet = _snippet(mail)

    if any(pattern.search(mail.from_addr) for pattern in _NOISE_FROM) and not _matches_any(
        hay, _ACK_PATTERNS + _REJECT_PATTERNS + _SCREENING_PATTERNS
    ):
        return MailEvent(
            kind=KIND_IGNORE,
            company=company,
            role_hint=role_hint,
            recruiter=recruiter,
            confidence=0.9,
            snippet=snippet,
            subject=mail.subject,
            from_addr=mail.from_addr,
            message_id=mail.message_id,
        )

    if _matches_any(hay, _REJECT_PATTERNS):
        return MailEvent(
            kind=KIND_REJECTED_HR,
            company=company,
            role_hint=role_hint,
            recruiter=recruiter,
            confidence=0.85 if company else 0.55,
            snippet=snippet,
            subject=mail.subject,
            from_addr=mail.from_addr,
            message_id=mail.message_id,
        )

    if _matches_any(hay, _SCREENING_PATTERNS):
        return MailEvent(
            kind=KIND_SCREENING,
            company=company,
            role_hint=role_hint,
            recruiter=recruiter,
            confidence=0.8 if company else 0.5,
            snippet=snippet,
            subject=mail.subject,
            from_addr=mail.from_addr,
            message_id=mail.message_id,
        )

    if _matches_any(hay, _ACK_PATTERNS):
        return MailEvent(
            kind=KIND_APPLICATION_ACK,
            company=company,
            role_hint=role_hint,
            recruiter=recruiter,
            confidence=0.85 if company else 0.55,
            snippet=snippet,
            subject=mail.subject,
            from_addr=mail.from_addr,
            message_id=mail.message_id,
        )

    if _looks_recruiter_mail(mail) and company:
        return MailEvent(
            kind=KIND_REPLIED,
            company=company,
            role_hint=role_hint,
            recruiter=recruiter,
            confidence=0.6,
            snippet=snippet,
            subject=mail.subject,
            from_addr=mail.from_addr,
            message_id=mail.message_id,
        )

    return MailEvent(
        kind=KIND_IGNORE,
        company=company,
        role_hint=role_hint,
        recruiter=recruiter,
        confidence=0.4,
        snippet=snippet,
        subject=mail.subject,
        from_addr=mail.from_addr,
        message_id=mail.message_id,
    )


def classify_from_headers(
    *,
    message_id: str,
    subject: str,
    from_header: str,
    body_text: str,
    date: str = "",
) -> MailEvent:
    name, addr = parseaddr(from_header)
    mail = InboundMail(
        message_id=message_id,
        subject=subject,
        from_addr=(addr or from_header).strip().lower(),
        from_name=name or "",
        date=date,
        body_text=body_text,
    )
    return classify_mail(mail)
