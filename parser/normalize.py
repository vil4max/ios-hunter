from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


_TRACKING_QUERY_KEYS = {
    "ref",
    "source",
    "gh_src",
    "sent",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "utm_reader",
}

_HOST_ALIASES = {
    "people.andersenlab.com": "people-andersenlab.com",
}


def canonicalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""

    split = urlsplit(raw)
    scheme = (split.scheme or "https").lower()
    host = (split.hostname or "").lower()
    host = _HOST_ALIASES.get(host, host)
    netloc = host
    if split.port and ((scheme == "http" and split.port != 80) or (scheme == "https" and split.port != 443)):
        netloc = f"{host}:{split.port}"

    path = split.path or "/"
    if path != "/":
        path = path.rstrip("/")

    query_items: list[tuple[str, str]] = []
    for key, value in parse_qsl(split.query, keep_blank_values=True):
        lowered_key = key.lower()
        if lowered_key.startswith("utm_"):
            continue
        if lowered_key in _TRACKING_QUERY_KEYS:
            continue
        query_items.append((key, value))

    query_items.sort(key=lambda kv: (kv[0], kv[1]))
    query = urlencode(query_items, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def compute_identity_key(
    *,
    company: str,
    canonical_url: str,
    source: str,
    source_job_id: str | None,
) -> tuple[str, str]:
    normalized_company = canonical_company(company)
    normalized_source = normalize_token(source)
    if source_job_id:
        raw = f"provider|{normalized_company}|{normalized_source}|{source_job_id.strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest(), "source_job_id"
    if canonical_url:
        raw = f"url|{normalized_company}|{canonical_url}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest(), "canonical_url"
    raw = f"fallback|{normalized_company}|{normalize_token(canonical_url)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest(), "fallback"


@dataclass
class Vacancy:
    company: str
    title: str
    url: str
    source: str
    location: str | None = None
    remote: str | None = None
    published_at: datetime | None = None
    description: str | None = None
    canonical_url: str = ""
    source_job_id: str | None = None
    identity_key: str = ""
    identity_strategy: str = ""
    ai_keyword_match: bool = False
    hash: str = field(default="", init=False)

    def __post_init__(self) -> None:
        self.canonical_url = self.canonical_url or canonicalize_url(self.url)
        if not self.identity_key:
            self.identity_key, self.identity_strategy = compute_identity_key(
                company=self.company,
                canonical_url=self.canonical_url,
                source=self.source,
                source_job_id=self.source_job_id,
            )
        self.hash = self.identity_key or compute_hash(self.company, self.title, self.location)


def normalize_title(title: str) -> str:
    without_ref = re.sub(r"\s*\(#\d+\)\s*$", "", title.strip())
    return re.sub(r"\s+", " ", without_ref).lower()


def role_key(company: str, title: str) -> tuple[str, str]:
    return canonical_company(company), normalize_title(title)


def compute_hash(company: str, title: str, location: str | None) -> str:
    raw = "|".join(
        [
            canonical_company(company),
            normalize_title(title),
            normalize_token(location or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_token(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


_COMPANY_ALIASES = {
    "n ix": "n-ix",
    "n i x": "n-ix",
    "nix": "n-ix",
    "n-ix": "n-ix",
    "chisw": "chi software",
    "chi software": "chi software",
    "globallogic": "globallogic",
    "global logic": "globallogic",
    "softserve": "softserve",
    "soft serve": "softserve",
    "sigma": "sigma software",
    "sigma software": "sigma software",
    "onix": "onix systems",
    "onix systems": "onix systems",
    "zone 3000": "zone3000",
    "zone3000": "zone3000",
    "eleks": "eleks",
    "grid dynamics": "grid dynamics",
    "griddynamics": "grid dynamics",
}


def canonical_company(value: str) -> str:
    token = normalize_token(value)
    collapsed = token.replace("-", " ")
    return _COMPANY_ALIASES.get(token) or _COMPANY_ALIASES.get(collapsed) or token


_IOS_ANCHOR = re.compile(
    r"(?i)(?<![a-z0-9])("
    r"ios|swift|swiftui|uikit|"
    r"objective[\s\-]?c|objc|obj[\s\-]?c|"
    r"xcode|iphone|ipad|tvos|watchos|visionos|"
    r"macos|mac\s*os|os\s*x|appkit|"
    r"cocoa(?:pods|touch)?"
    r")(?![a-z0-9])"
)

_NON_IOS_ROLE_TITLE = re.compile(
    r"(?i)(?<![a-z0-9])(qa|sdet|tpm|"
    r"quality\s+assurance|"
    r"test(?:ing)?\s+(?:automation|engineer|developer)|"
    r"automation\s+(?:qa|engineer|tester)|"
    r"manual\s+qa|"
    r"mobile\s+automation"
    r")(?![a-z0-9])"
)

_AI_AUGMENTED_SIGNAL = re.compile(
    r"(?i)\b(?:"
    r"ai[- ]augmented|"
    r"agentic(?:\s+ai)?|"
    r"multi[- ]agent|autonomous\s+agent|agent\s+orchestration|"
    r"mcp|model\s+context\s+protocol|"
    r"ai\s+orchestrat(?:ion|or)|ai\s+sdlc|"
    r"ai[- ](?:native|first|powered|driven)|"
    r"ai\s+(?:software\s+|full[-\s]?stack\s+|backend\s+|frontend\s+|web\s+)?(?:developer|engineer)|"
    r"llm|applied\s+ai|ai\s+(?:platform|integration|solutions?)"
    r")\b"
)
# Assistant tool names alone are too generic (SQL "cursor"): require a
# separate generic AI mention alongside them.
_AI_ASSISTANT_TOOL_SIGNAL = re.compile(
    r"(?i)\b(?:cursor|copilot|claude\s+code|codex|windsurf|coding\s+agent)\b"
)
_GENERIC_AI_MENTION = re.compile(
    r"(?i)\b(?:ai|artificial\s+intelligence|llm|agent)\b"
)
_AI_AUGMENTED_ENGINEERING = re.compile(
    r"(?i)\b(?:software|full[- ]stack|backend|frontend|web\s+(?:developer|engineer)|"
    r"javascript|typescript|node(?:\.js)?|engineering|engineer|developer|architect)\b"
)
_AI_AUGMENTED_EXCLUDED = re.compile(
    r"(?i)\b(?:machine learning|ml engineer|data scientist|deep learning|"
    r"computer vision|nlp engineer|python[- ]only|"
    r"qa|sdet|quality\s+assurance|tester|advocate|devrel|manager)\b"
)

_BODY_ROLE = re.compile(
    r"(?i)(?<![a-z0-9а-яіїєґ])("
    r"mobile|native|"
    r"software\s+(?:engineer|developer)|"
    r"client[\s\-]?side"
    r")(?![a-z0-9а-яіїєґ])"
)

_JUNIOR_TITLE = re.compile(
    r"(?i)(?<![a-z0-9а-яіїєґ])("
    r"junior|jr\.?|intern|internship|trainee|стажер|інтерн|джуніор|"
    r"без\s+(?:досвіду|опыта)|no\s+experience|entry[\s\-]?level"
    r")(?![a-z0-9а-яіїєґ])"
)

_SENIORISH_TITLE = re.compile(
    r"(?i)(?<![a-z0-9а-яіїєґ])("
    r"senior|sr\.?|lead|staff|principal|head|architect"
    r")(?![a-z0-9а-яіїєґ])"
)

_APPLE_CORE = re.compile(
    r"(?i)(?<![a-z0-9])("
    r"ios|swift|swiftui|uikit|"
    r"objective[\s\-]?c|objc|obj[\s\-]?c|"
    r"appkit|cocoa(?:pods|touch)?"
    r")(?![a-z0-9])"
)

_CROSS_PLATFORM_TITLE = re.compile(
    r"(?i)(?:"
    r"\bios\s*(?:/|&|and)\s*android\b|"
    r"\bandroid\s*(?:/|&|and)\s*ios\b|"
    r"\bios\s+(?:developer|engineer)\s+with\s+android\b|"
    r"\breact\s+native\s+(?:developer|engineer)\b|"
    r"\b(?:kmm|kotlin\s+multiplatform)\s+(?:developer|engineer)\b|"
    r"\bflutter\s+(?:developer|engineer)\b"
    r")"
)

_TARGET_LOCATION = re.compile(
    r"(?i)\b(?:"
    r"ukraine|ukrainian|kyiv|kiev|lviv|kharkiv|kharkov|dnipro|dnepr|"
    r"odesa|odessa|vinnytsia|vinnitsa|ivano-frankivsk|uzhhorod|chernivtsi|"
    r"cherkasy|poltava|zaporizhzhia|ternopil|rivne|lutsk|mykolaiv|"
    r"worldwide|anywhere|global|emea|europe|european|"
    r"україн\w*|украин\w*|київ|киев|львів|львов|харків|харьков|дніпро|днепр|"
    r"одеса|одесса|вінниця|винница"
    r")\b"
)

def is_ios_job(title: str, description: str | None = None) -> bool:
    title_text = title or ""
    if _NON_IOS_ROLE_TITLE.search(title_text):
        return False
    if _IOS_ANCHOR.search(title_text):
        return True
    if description and _APPLE_CORE.search(description) and _BODY_ROLE.search(title_text):
        return True
    return False


def is_ai_augmented_job(title: str, description: str | None = None) -> bool:
    text = f"{title} {description or ''}"
    if _AI_AUGMENTED_EXCLUDED.search(title):
        return False
    if not _AI_AUGMENTED_ENGINEERING.search(text):
        return False
    if (_AI_AUGMENTED_ENGINEERING.search(title) and _GENERIC_AI_MENTION.search(title)):
        return True
    if _AI_AUGMENTED_SIGNAL.search(text):
        return True
    return bool(
        _AI_ASSISTANT_TOOL_SIGNAL.search(text)
        and _GENERIC_AI_MENTION.search(text)
    )


def is_ai_augmented_only(
    title: str,
    description: str | None = None,
    *,
    ai_keyword_match: bool = False,
) -> bool:
    if is_ios_job(title, description):
        return False
    return is_ai_augmented_job(title, description) or ai_keyword_match


def is_ai_keyword_candidate(title: str, card_text: str = "") -> bool:
    """Fallback for a server-side AI keyword search: the listing is already
    AI-filtered, so accept any engineering role whose card still mentions AI."""
    if _AI_AUGMENTED_EXCLUDED.search(title):
        return False
    if not _AI_AUGMENTED_ENGINEERING.search(title):
        return False
    return bool(_GENERIC_AI_MENTION.search(f"{title} {card_text}"))


def is_target_level(title: str) -> bool:
    text = title or ""
    if _JUNIOR_TITLE.search(text) and not _SENIORISH_TITLE.search(text):
        return False
    return True


def is_primary_ios_role(title: str) -> bool:
    return is_ios_job(title) and not _CROSS_PLATFORM_TITLE.search(title or "")


def is_target_location(location: str | None) -> bool:
    value = (location or "").strip()
    return not value or bool(_TARGET_LOCATION.search(value))


def is_inbox_candidate(vacancy: Vacancy) -> bool:
    return (
        (
            is_primary_ios_role(vacancy.title)
            or is_ai_augmented_job(vacancy.title, vacancy.description)
        )
        and (is_primary_ios_role(vacancy.title) or not ai_requirement_blockers(vacancy.title, vacancy.description or ""))
        and is_target_location(vacancy.location)
    )


def infer_remote(title: str, location: str | None, description: str | None) -> str:
    text = f"{title} {location or ''} {description or ''}".lower()
    if any(word in text for word in ("remote", "remotely")):
        return "remote"
    if "hybrid" in text:
        return "hybrid"
    if any(word in text for word in ("onsite", "office")):
        return "onsite"
    return "unknown"


def normalize_raw(raw: dict[str, Any]) -> Vacancy | None:
    title = str(raw.get("title", "")).strip()
    company = str(raw.get("company", "")).strip()
    url = str(raw.get("url", "")).strip()
    if not title or not company or not url:
        return None

    description = raw.get("description")
    if description is not None:
        description = str(description).strip() or None

    if not is_ios_job(title, description) and ai_requirement_blockers(title, description or ""):
        return None

    ai_keyword_match = bool(raw.get("ai_keyword_match"))
    if not (
        is_ios_job(title, description)
        or is_ai_augmented_job(title, description)
        or (ai_keyword_match and is_ai_keyword_candidate(title, description or ""))
    ):
        return None
    if not is_target_level(title):
        return None

    location = raw.get("location")
    location = str(location).strip() if location else None
    remote = raw.get("remote") or infer_remote(title, location, description)

    published_at = None
    if raw.get("published_at"):
        try:
            published_at = datetime.fromisoformat(str(raw["published_at"]).replace("Z", "+00:00"))
        except ValueError:
            published_at = None

    source_job_id: str | None = None
    raw_source_job_id = raw.get("source_job_id") or raw.get("job_id") or raw.get("id")
    if raw_source_job_id is not None:
        source_job_id = str(raw_source_job_id).strip() or None

    return Vacancy(
        company=company,
        title=title,
        url=url,
        source=str(raw.get("source", "company")),
        location=location,
        remote=str(remote),
        published_at=published_at,
        description=description,
        source_job_id=source_job_id,
        ai_keyword_match=ai_keyword_match,
    )


def normalize_many(raw_jobs: list[dict[str, Any]]) -> list[Vacancy]:
    vacancies: list[Vacancy] = []
    for raw in raw_jobs:
        vacancy = normalize_raw(raw)
        if vacancy:
            vacancies.append(vacancy)
    return vacancies


def is_target_job(title: str, description: str | None = None) -> bool:
    """Shared early collector gate; preserve the original iOS predicate."""
    return is_ios_job(title, description) or (
        is_ai_augmented_job(title, description)
        and not ai_requirement_blockers(title, description or "")
    )


def ai_negative_signals(title: str, description: str = "") -> tuple[str, ...]:
    signals = []
    if re.search(r"\b(?:data scien(?:ce|tist)|research|computer vision|nlp|mlops)\b", title, re.I):
        signals.append("specialist Data Science/research/MLOps title")
    for sentence in re.split(r"[.\n;]", description):
        if re.search(r"\b(?:not required|optional|nice.to.have|preferred|no need)\b", sentence, re.I):
            continue
        if re.search(r"\b(?:primary|primarily|heavy|focus|core|main)\b", sentence, re.I) and re.search(
            r"\b(?:model training|training models|mlops|computer vision|nlp research|ml research|data science)\b", sentence, re.I
        ):
            signals.append("research/model-training/MLOps-heavy responsibilities")
        if (re.search(r"\b(?:must|required|mandatory|minimum|at least)\b", sentence, re.I)
            and re.search(r"\b(?:commercial|professional|production)\b", sentence, re.I)
            and re.search(r"\b(?:python|ml|machine learning)\b", sentence, re.I)
            and re.search(r"\b(?:[3-9]|[1-9][0-9])(?:\s*[-–]\s*\d+)?\s*\+?\s*(?:years?|yrs?)\b", sentence, re.I)):
            signals.append("mandatory 3+ years commercial Python/ML experience needs evidence")
    return tuple(dict.fromkeys(signals))


def required_ai_text(description: str) -> str:
    """Keep requirement sections and exclude explicitly optional bullets."""
    from bs4 import BeautifulSoup

    document = BeautifulSoup(description or "", "html.parser")
    for node in document.find_all(["p", "li", "div", "h1", "h2", "h3", "h4", "br"]):
        node.insert_after("\n")
    text = document.get_text(" ")
    required = []
    optional_section = False
    for line in re.split(r"[\n;]|(?<=[.!?])\s+", text):
        line = line.strip()
        if re.search(r"^(?:nice.to.have|preferred qualifications|bonus|desirable)\b", line, re.I):
            optional_section = True
            continue
        if re.search(r"^(?:requirements|responsibilities|qualifications|personal profile|required skills)\b", line, re.I):
            optional_section = False
        if optional_section or re.search(r"\b(?:not required|optional|preferred|also acceptable|other languages|nice.to.have)\b", line, re.I):
            continue
        required.append(line)
    return "\n".join(required)


def ai_requirement_blockers(title: str, description: str = "") -> tuple[str, ...]:
    text = required_ai_text(description)
    blockers = []
    if _AI_AUGMENTED_EXCLUDED.search(title) or re.search(r"\b(?:research scientist|mlops engineer|data science)\b", title, re.I):
        blockers.append("ML/research specialist role")
    for line in text.splitlines():
        if re.search(r"\b(?:train(?:ing)?|develop(?:ing)?|build(?:ing)?)\s+(?:(?:custom|new|ml|machine learning|deep learning)\s+)*(?:models?|neural networks)\b", line, re.I):
            blockers.append("required ML model development")
        if re.search(
            r"\b(?:strong|deep|advanced|expert|proficien\w*|extensive)\s+"
            r"(?:(?:knowledge|understanding|experience|expertise|proficiency|skills|in|of|with)\s+){0,4}python\b"
            r"|\bpython\s+(?:expertise|proficiency|mastery)\b",
            line, re.I,
        ):
            blockers.append("required strong Python")
    blockers.extend(ai_negative_signals(title, text))
    return tuple(dict.fromkeys(blockers))
