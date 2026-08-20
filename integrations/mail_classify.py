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
    (re.compile(r"\bn[-\s]ix\b", re.I), "N-iX"),
    (re.compile(r"\bnix\b", re.I), "NIX"),
    (re.compile(r"\blineup\b", re.I), "LineUp"),
    (re.compile(r"\bgrammarly\b", re.I), "Grammarly"),
    (re.compile(r"\bsoftserve\b", re.I), "SoftServe"),
    (re.compile(r"\bepam\b", re.I), "EPAM"),
    (re.compile(r"\bintellias\b", re.I), "Intellias"),
    (re.compile(r"\bciklum\b", re.I), "Ciklum"),
    (re.compile(r"\bgloballogic\b", re.I), "GlobalLogic"),
    (re.compile(r"\bbetterme\b", re.I), "BetterMe"),
    (re.compile(r"\bnorthstrat\b", re.I), "Northstrat"),
)

_APPLYING_TO = re.compile(
    r"(?:thanks?\s+for\s+applying\s+to|thank\s+you\s+for\s+applying\s+to|"
    r"applying\s+to|application\s+to)\s+([A-Z][A-Za-z0-9&.'\- ]{1,60})",
    re.I,
)

_REJECT_PATTERNS = (
    re.compile(r"not\s+(be\s+)?(able\s+to\s+)?proceed", re.I),
    re.compile(r"will\s+not\s+be\s+moving\s+forward", re.I),
    re.compile(r"decided\s+to\s+(move|go)\s+forward\s+with\s+(other|another)", re.I),
    re.compile(r"other\s+candidates", re.I),
    re.compile(r"not\s+selected", re.I),
    re.compile(r"position\s+has\s+been\s+filled", re.I),
    re.compile(r"we\s+regret\s+to\s+inform", re.I),
    re.compile(r"(?:відмовили|відхилили).{0,60}(?:кандидатур|відгук|заявк)", re.I),
    re.compile(r"не\s+будем\s+продолжать", re.I),
    re.compile(r"не\s+будемо\s+продовжувати", re.I),
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
    re.compile(r"отримали\s+ваше\s+резюме", re.I),
    re.compile(r"отклик\s+получен", re.I),
)

_RECRUITER_HINTS = (
    re.compile(r"recruit", re.I),
    re.compile(r"talent\s+acquisition", re.I),
    re.compile(r"\bhr\s+(team|department|manager|bp)\b", re.I),
    re.compile(r"\bhr@", re.I),
    re.compile(r"\bhiring\b", re.I),
    re.compile(r"careers?@", re.I),
    re.compile(r"jobs?@", re.I),
)

_APPLICATION_SIGNALS = (
    re.compile(r"\bjob\s+application\b", re.I),
    re.compile(r"\byour\b.{0,40}\bapplication\b", re.I),
    re.compile(r"\bapplication\s+to\b", re.I),
    re.compile(r"\bapplication\s+(has\s+been\s+)?received\b", re.I),
    re.compile(r"\bupdate\s+on\s+your\s+application\b", re.I),
    re.compile(r"\bregarding\s+your\s+application\b", re.I),
    re.compile(r"\bregarding\s+(the\s+)?(open\s+)?position\b", re.I),
    re.compile(r"\bthanks?\s+for\s+apply", re.I),
    re.compile(r"\bthank\s+you\s+for\s+(your\s+)?(application|applying|interest)\b", re.I),
    re.compile(r"\bthanks?\s+for\s+(your\s+)?interest\b", re.I),
    re.compile(r"\b(we\s+)?received\s+your\s+application\b", re.I),
    re.compile(r"\bmoving\s+forward\s+with\s+your\s+application\b", re.I),
    re.compile(r"\byour\s+(cv|resume|portfolio)\b", re.I),
    re.compile(r"\breviewed\s+your\s+(cv|resume|portfolio|profile)\b", re.I),
    re.compile(r"\bcandidacy\b", re.I),
    re.compile(r"\bвідгук", re.I),
    re.compile(r"\bотклик", re.I),
    re.compile(r"\bзаявк", re.I),
    re.compile(r"\bваканс", re.I),
    re.compile(r"\bрезюме\b", re.I),
    re.compile(r"\bкандидатур", re.I),
    re.compile(r"дякуємо\s+за\s+(відгук|заявку|інтерес)", re.I),
    re.compile(r"спасибо\s+за\s+(отклик|интерес|заявку)", re.I),
    re.compile(r"ваш[ау]?\s+(відгук|заявк|отклик)", re.I),
)

_SERVICE_NOISE_PATTERNS = (
    re.compile(r"two[- ]?(step|factor)\s+(verif|auth)", re.I),
    re.compile(r"\b2[- ]?step\s+verif", re.I),
    re.compile(r"\b2fa\b", re.I),
    re.compile(r"двухэтапн\w*\s+аутентификац", re.I),
    re.compile(r"двухфакторн\w*\s+аутентификац", re.I),
    re.compile(r"включил[аи]?\s+двухэтапн", re.I),
    re.compile(r"password\s+(reset|changed|updated)", re.I),
    re.compile(r"reset\s+your\s+password", re.I),
    re.compile(r"security\s+(alert|code|notification|notice)", re.I),
    re.compile(r"verification\s+code", re.I),
    re.compile(r"one[- ]time\s+code", re.I),
    re.compile(r"confirm\s+your\s+identity", re.I),
    re.compile(r"code\s+will\s+expire", re.I),
    re.compile(r"verify\s+and\s+you", re.I),
    re.compile(r"quick\s+step", re.I),
    re.compile(r"код\s+подтверждения", re.I),
    re.compile(r"confirm\s+your\s+(email|account)", re.I),
    re.compile(r"signed\s+in\s+from\s+a\s+new", re.I),
    re.compile(r"new\s+sign[- ]?in\s+(to|on)\s+your", re.I),
    re.compile(r"ssh\s+(key|authentication)", re.I),
)

_BILLING_NOISE_PATTERNS = (
    re.compile(r"\bквитанц", re.I),
    re.compile(r"\bосбб\b", re.I),
    re.compile(r"\bоплат[аиуы]?\b", re.I),
    re.compile(r"\bкредит\b", re.I),
    re.compile(r"\bпумб\b", re.I),
    re.compile(r"privatbank|приватбанк|monobank|ощадбанк", re.I),
    re.compile(r"\binvoice\b", re.I),
    re.compile(r"\breceipt\b", re.I),
    re.compile(r"завантаження\s+документ", re.I),
    re.compile(r"топ[- ]?найми", re.I),
    re.compile(r"\bdjinni\b", re.I),
    re.compile(r"@djinni\.co", re.I),
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

_DIGEST_NOISE_PATTERNS = (
    re.compile(r"нових\s+ваканс", re.I),
    re.compile(r"новых\s+ваканс", re.I),
    re.compile(r"і\s+ще\s+\d+\s+нов", re.I),
    re.compile(r"и\s+еще\s+\d+\s+нов", re.I),
    re.compile(r"vacancy\s+digest", re.I),
    re.compile(r"job\s+alert", re.I),
    re.compile(r"jobs?\s+you\s+may\s+like", re.I),
    re.compile(r"recommended\s+jobs", re.I),
    re.compile(r"new\s+jobs?\s+for\s+you", re.I),
)

_NOISE_FROM = (
    re.compile(r"noreply@", re.I),
    re.compile(r"no-reply@", re.I),
    re.compile(r"no-reply-", re.I),
    re.compile(r"newsletter@", re.I),
    re.compile(r"notifications?@", re.I),
    re.compile(r"linkedin\.com", re.I),
    re.compile(r"facebookmail\.com", re.I),
    re.compile(r"jooble\.", re.I),
    re.compile(r"@jooble\.", re.I),
    re.compile(r"ciklumcareer@", re.I),
    re.compile(r"no-reply-ciklumcareer@", re.I),
)

_NOISE_DOMAINS = frozenset({"indeed.com"})

_FOOTER_START_PATTERNS = (
    re.compile(r"^\s*unsubscribe\b", re.I),
    re.compile(r"^\s*відмовитися\s+від\s+(?:повідомлень|розсилки)", re.I),
    re.compile(r"^\s*отписаться\s+от\s+(?:сообщений|рассылки)", re.I),
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


def _body_without_footer(mail: InboundMail) -> str:
    lines: list[str] = []
    for line in mail.body_text[:4000].splitlines():
        if _matches_any(line, _FOOTER_START_PATTERNS):
            break
        lines.append(line)
    return "\n".join(lines)


def _blob(mail: InboundMail) -> str:
    return f"{mail.subject}\n{mail.from_name}\n{mail.from_addr}\n{_body_without_footer(mail)}"


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
    domain = _domain(mail.from_addr)
    if domain in _DOMAIN_COMPANY:
        return _DOMAIN_COMPANY[domain]
    parts = domain.split(".")
    if len(parts) >= 3:
        parent = ".".join(parts[-2:])
        if parent in _DOMAIN_COMPANY:
            return _DOMAIN_COMPANY[parent]

    hay = f"{mail.subject}\n{mail.from_name}\n{mail.body_text[:1500]}"
    for pattern, company in _SUBJECT_COMPANY:
        if pattern.search(hay):
            return company

    applying = _APPLYING_TO.search(f"{mail.subject}\n{mail.body_text[:800]}")
    if applying:
        name = re.sub(r"\s+", " ", applying.group(1)).strip(" -–,.")
        name = re.split(r"[.!?\n|]", name, maxsplit=1)[0].strip()
        if 2 <= len(name) <= 60 and name.lower() not in {"us", "our", "the", "your"}:
            return name

    name = (mail.from_name or "").strip()
    if name and not re.search(r"recruit|talent|hr team|careers|noreply|no-reply|hiring team", name, re.I):
        cleaned = re.sub(r"\s*(recruitment|talent|hr|team)\s*$", "", name, flags=re.I).strip()
        if cleaned and len(cleaned) <= 40:
            return cleaned

    if any(domain == ats or domain.endswith("." + ats) for ats in _ATS_DOMAINS):
        return ""

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


def _is_ats_domain(domain: str) -> bool:
    return any(domain == ats or domain.endswith("." + ats) for ats in _ATS_DOMAINS)


def _is_noise_sender(mail: InboundMail) -> bool:
    domain = _domain(mail.from_addr)
    if any(domain == noise or domain.endswith("." + noise) for noise in _NOISE_DOMAINS):
        return True
    return any(pattern.search(mail.from_addr) for pattern in _NOISE_FROM)


def _has_sender_hiring_signal(mail: InboundMail) -> bool:
    hay = f"{mail.from_name}\n{mail.from_addr}\n{mail.subject}"
    if _matches_any(hay, _RECRUITER_HINTS):
        return True
    domain = _domain(mail.from_addr)
    if domain in _DOMAIN_COMPANY:
        return True
    parts = domain.split(".")
    if len(parts) >= 3:
        parent = ".".join(parts[-2:])
        if parent in _DOMAIN_COMPANY:
            return True
    if _is_ats_domain(domain):
        return True
    if re.search(r"(jobs?|careers?|recruit)", mail.from_addr, re.I):
        return True
    return False


def _has_application_signal(mail: InboundMail) -> bool:
    hay = _blob(mail)
    if _matches_any(hay, _APPLICATION_SIGNALS):
        return True
    if _matches_any(hay, _ACK_PATTERNS):
        return True
    if _APPLYING_TO.search(f"{mail.subject}\n{mail.body_text[:800]}"):
        return True
    return False


def _is_application_thread(mail: InboundMail) -> bool:
    if _has_application_signal(mail):
        return True
    hay = _blob(mail)
    if _has_sender_hiring_signal(mail) and _matches_any(
        hay, _REJECT_PATTERNS + _SCREENING_PATTERNS + _ACK_PATTERNS
    ):
        return True
    return False


def _ignore_event(
    mail: InboundMail,
    *,
    company: str,
    role_hint: str,
    recruiter: str,
    snippet: str,
    confidence: float,
) -> MailEvent:
    return MailEvent(
        kind=KIND_IGNORE,
        company=company,
        role_hint=role_hint,
        recruiter=recruiter,
        confidence=confidence,
        snippet=snippet,
        subject=mail.subject,
        from_addr=mail.from_addr,
        message_id=mail.message_id,
    )


def classify_mail(mail: InboundMail) -> MailEvent:
    hay = _blob(mail)
    company = extract_company(mail)
    role_hint = extract_role_hint(mail)
    recruiter = extract_recruiter(mail)
    snippet = _snippet(mail)

    if re.search(r"jooble\.", mail.from_addr, re.I) or re.search(r"\bjooble\b", mail.subject, re.I):
        return _ignore_event(
            mail,
            company=company,
            role_hint=role_hint,
            recruiter=recruiter,
            snippet=snippet,
            confidence=0.95,
        )

    if (
        _matches_any(hay, _SERVICE_NOISE_PATTERNS)
        or _matches_any(hay, _BILLING_NOISE_PATTERNS)
        or _matches_any(hay, _DIGEST_NOISE_PATTERNS)
    ):
        return _ignore_event(
            mail,
            company=company,
            role_hint=role_hint,
            recruiter=recruiter,
            snippet=snippet,
            confidence=0.95,
        )

    application_thread = _is_application_thread(mail)

    if _is_noise_sender(mail) and not (
        application_thread
        and _matches_any(hay, _ACK_PATTERNS + _REJECT_PATTERNS + _SCREENING_PATTERNS)
    ):
        return _ignore_event(
            mail,
            company=company,
            role_hint=role_hint,
            recruiter=recruiter,
            snippet=snippet,
            confidence=0.9,
        )

    if application_thread and _matches_any(hay, _REJECT_PATTERNS):
        return MailEvent(
            kind=KIND_REJECTED_HR,
            company=company,
            role_hint=role_hint,
            recruiter=recruiter,
            confidence=0.95 if company else 0.7,
            snippet=snippet,
            subject=mail.subject,
            from_addr=mail.from_addr,
            message_id=mail.message_id,
        )

    if application_thread and _matches_any(hay, _SCREENING_PATTERNS):
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

    if application_thread and _matches_any(hay, _ACK_PATTERNS):
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

    if company and (
        _has_application_signal(mail)
        or (_has_sender_hiring_signal(mail) and bool(role_hint))
    ):
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

    return _ignore_event(
        mail,
        company=company,
        role_hint=role_hint,
        recruiter=recruiter,
        snippet=snippet,
        confidence=0.4,
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
