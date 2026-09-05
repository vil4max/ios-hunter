from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path

from config.search_tracks import AI_RELEVANCE_PATTERNS
from parser.normalize import Vacancy, is_ai_augmented_only, ai_negative_signals, ai_requirement_blockers, required_ai_text


@dataclass(frozen=True)
class CandidateProfile:
    years_ios: int
    skills: frozenset[str]
    preferred_role: str
    home_location: str
    remote_preferred: bool
    english_public_level: str
    excluded_domains: frozenset[str]


@dataclass(frozen=True)
class FitAssessment:
    score: int
    recommendation: str
    confidence: str
    reasons: tuple[str, ...]
    blockers: tuple[str, ...]
    english_requirement: str


_SKILL_PATTERNS = {
    "swift": r"\bswift\b",
    "swiftui": r"\bswiftui\b",
    "uikit": r"\buikit\b",
    "swift concurrency": r"\b(?:swift concurrency|async/?await|actors?)\b",
    "spm": r"\b(?:spm|swift package manager)\b",
    "modularization": r"\b(?:modulari[sz]ation|modular architecture|modules?)\b",
    "watchconnectivity": r"\bwatchconnectivity\b",
    "realtime audio streaming": r"\b(?:realtime|real-time).{0,30}\baudio\b",
}
_SENIOR = re.compile(r"\b(senior|sr\.?|lead|staff|principal|architect)\b", re.I)
_MIDDLE = re.compile(r"\b(middle|mid-level|mid level)\b", re.I)
_JUNIOR = re.compile(r"\b(junior|jr\.?|intern|trainee)\b", re.I)
_YEARS = re.compile(r"\b(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", re.I)
_REMOTE = re.compile(r"\b(remote|worldwide|anywhere|work from home)\b", re.I)
_GLOBAL_REMOTE = re.compile(r"\b(worldwide|anywhere|global remote|emea|europe)\b", re.I)
_UKRAINE = re.compile(
    r"\b(?:ukraine|ukrainian|kyiv|kiev|lviv|kharkiv|kharkov|dnipro|dnepr|"
    r"odesa|odessa|vinnytsia|vinnitsa|ivano-frankivsk|uzhhorod|chernivtsi|"
    r"cherkasy|poltava|zaporizhzhia|ternopil|rivne|lutsk|mykolaiv|"
    r"україн\w*|украин\w*|київ|киев|львів|львов|харків|харьков|дніпро|днепр|"
    r"одеса|одесса|вінниця|винница|івано-франківськ|ивано-франковск|ужгород|"
    r"чернівці|черновцы|черкаси|черкассы|полтава|запоріжжя|запорожье|"
    r"тернопіль|тернополь|рівне|ровно|луцьк|луцк|миколаїв|николаев)\b",
    re.I,
)
_KYIV_HYBRID = re.compile(r"\b(kyiv|kiev)\b.*\bhybrid\b|\bhybrid\b.*\b(kyiv|kiev)\b", re.I)
_ENGLISH_ADVANCED = re.compile(r"\b(c1|advanced english|fluent english)\b", re.I)
_ENGLISH_B2 = re.compile(r"\b(b2|upper.intermediate)\b", re.I)
_ENGLISH_LEVEL = re.compile(r"\b(a1|a2|b1|b2|c1|c2)\b", re.I)


def _plain_text(value: str) -> str:
    without_tags = re.sub(r"(?s)<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(without_tags)).strip()


def load_candidate_profile(resume_path: Path, career_path: Path) -> CandidateProfile:
    resume = resume_path.read_text(encoding="utf-8")
    career = career_path.read_text(encoding="utf-8")
    years_match = re.search(r"approved public experience framing is `([0-9]+)\+ years`", career)
    skills = {
        match.group(1).strip().lower()
        for match in re.finditer(r"\[GENERAL_SKILL\]\*\*\s*([^\n]+)", career)
    }
    if not skills:
        skills_section = resume.partition("## Skills")[2].partition("## Roles")[0]
        skills = {part.strip().lower() for part in skills_section.split("·") if part.strip()}
    excluded = frozenset(
        domain
        for domain in ("gambling", "dating")
        if domain in career.lower()
    )
    return CandidateProfile(
        years_ios=int(years_match.group(1)) if years_match else 10,
        skills=frozenset(skills),
        preferred_role="Senior iOS Engineer",
        home_location="Kyiv, Ukraine",
        remote_preferred="Remote is the primary and strongly preferred" in career,
        english_public_level="B2",
        excluded_domains=excluded,
    )


def _role_score(title: str) -> tuple[int, list[str], list[str]]:
    reasons: list[str] = []
    blockers: list[str] = []
    if _JUNIOR.search(title):
        blockers.append("junior-only title")
        return 0, reasons, blockers
    if _SENIOR.search(title):
        reasons.append("seniority matches Senior+ target")
        return 30, reasons, blockers
    if _MIDDLE.search(title):
        reasons.append("Middle title is eligible; validate scope and compensation")
        return 23, reasons, blockers
    reasons.append("iOS role without explicit seniority")
    return 23, reasons, blockers


def _stack_score(text: str, profile: CandidateProfile) -> tuple[int, list[str]]:
    matched = [
        skill
        for skill, pattern in _SKILL_PATTERNS.items()
        if skill in profile.skills and re.search(pattern, text, re.I)
    ]
    score = min(25, 10 + len(matched) * 3)
    detail = ", ".join(matched) if matched else "iOS signal only; detailed stack unavailable"
    return score, [f"stack evidence: {detail}"]


def _experience_score(text: str, profile: CandidateProfile) -> tuple[int, list[str]]:
    requirements = [int(match.group(1)) for match in _YEARS.finditer(text)]
    if not requirements:
        return 12, ["required years not stated"]
    required = max(requirements)
    if required <= profile.years_ios:
        return 15, [f"experience requirement {required}+ years is covered"]
    return 7, [f"experience requirement {required}+ exceeds public {profile.years_ios}+ framing"]


def _work_mode_score(vacancy: Vacancy, text: str) -> tuple[int, list[str], list[str]]:
    location = (vacancy.location or "").strip()
    remote = (vacancy.remote or "").strip()
    combined = " ".join((location, remote, text[:1500]))
    if location and not _UKRAINE.search(location) and not _GLOBAL_REMOTE.search(location):
        return 0, [f"concrete non-UA location: {location}"], ["location mismatch"]
    if _REMOTE.search(remote) or _REMOTE.search(location):
        return 20, ["remote work signal"], []
    if _KYIV_HYBRID.search(combined):
        return 12, ["Kyiv hybrid is possible but low preference"], []
    if _UKRAINE.search(location):
        return 18, [f"Ukraine location: {location}"], []
    if location:
        return 0, [f"concrete non-UA location: {location}"], ["location mismatch"]
    return 10, ["work location is unclear"], []


def _english_requirement(text: str) -> str:
    level = _ENGLISH_LEVEL.search(text)
    if level:
        return level.group(1).upper()
    if _ENGLISH_ADVANCED.search(text):
        return "C1"
    if _ENGLISH_B2.search(text):
        return "B2"
    return "unspecified"


def assess_fit(vacancy: Vacancy, profile: CandidateProfile) -> FitAssessment:
    title = _plain_text(vacancy.title)
    description = _plain_text(vacancy.description or "")
    text = f"{title} {description}"
    score = 0
    reasons: list[str] = []
    blockers: list[str] = []

    role_points, role_reasons, role_blockers = _role_score(title)
    score += role_points
    reasons.extend(role_reasons)
    blockers.extend(role_blockers)

    ai_track = is_ai_augmented_only(title, description, ai_keyword_match=vacancy.ai_keyword_match)
    stack_points, stack_reasons = _stack_score(text, profile)
    if ai_track:
        matched = [name for name, pattern in AI_RELEVANCE_PATTERNS.items() if re.search(pattern, text, re.I)]
        stack_points = min(25, 4 + 3 * len(matched))
        stack_reasons = ["AI opportunity signals (not proven candidate skills): " + (", ".join(matched) or "unspecified")]
        reasons = [reason.replace("iOS role", "AI role") for reason in reasons]
        reasons.append("secondary Applied AI track; iOS remains primary")
        score -= 5
        negatives = ai_negative_signals(title, required_ai_text(vacancy.description or ""))
        blockers.extend(ai_requirement_blockers(title, vacancy.description or ""))
        score -= 15 * len(negatives)
        reasons.extend(negatives)
    score += stack_points
    reasons.extend(stack_reasons)

    experience_points, experience_reasons = _experience_score(text, profile)
    if ai_track:
        experience_points = 7
        experience_reasons = ["AI/Python commercial experience unverified; iOS years are not substituted"]
    score += experience_points
    reasons.extend(experience_reasons)

    work_points, work_reasons, work_blockers = _work_mode_score(vacancy, text)
    score += work_points
    reasons.extend(work_reasons)
    blockers.extend(work_blockers)

    english_requirement = _english_requirement(text)
    score += 5
    reasons.append(f"English required: {english_requirement}")

    matched_excluded = [domain for domain in profile.excluded_domains if domain in text.lower()]
    if matched_excluded:
        blockers.append(f"excluded domain: {', '.join(sorted(matched_excluded))}")
    else:
        score += 5

    if ai_track:
        requirements = required_ai_text(vacancy.description or "")
        gaps = []
        for skill, pattern in {
            "JavaScript": r"\bjavascript\b", "TypeScript": r"\btypescript\b",
            "MCP": r"\bmcp\b", "AI orchestration": r"\borchestration\b",
            "multi-agent systems": r"\bmulti.agent\b", "AI SDLC": r"\bai sdlc\b",
            "client-facing communication": r"\b(?:consulting|client.facing)\b",
        }.items():
            if re.search(pattern, requirements, re.I) and skill.lower() not in profile.skills:
                gaps.append(skill)
        if gaps:
            reasons.append("Required skills need evidence: " + ", ".join(gaps))
            score = min(score, 77)
        if not description:
            reasons.append("Full requirements unavailable; manual review needed")
            score = min(score, 77)
    score = max(0, min(100, score))
    if blockers:
        recommendation = "skip"
    elif score >= 78:
        recommendation = "strong"
    elif score >= 62:
        recommendation = "review"
    else:
        recommendation = "weak"
    confidence = "high" if len(description) >= 500 and vacancy.location else "medium"
    if len(description) < 120:
        confidence = "low"
    return FitAssessment(
        score=score,
        recommendation=recommendation,
        confidence=confidence,
        reasons=tuple(reasons),
        blockers=tuple(blockers),
        english_requirement=english_requirement,
    )
