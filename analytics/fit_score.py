from __future__ import annotations

import json
import re
from datetime import datetime
from dataclasses import dataclass
from html import unescape
from pathlib import Path

from config.search_tracks import AI_RELEVANCE_PATTERNS
from parser.normalize import Vacancy, is_ai_augmented_only, ai_negative_signals, ai_requirement_blockers, required_ai_text, is_location_eligible, has_ai_job_details


@dataclass(frozen=True)
class CandidateProfile:
    years_ios: int
    skills: frozenset[str]
    preferred_role: str
    home_location: str
    remote_preferred: bool
    english_public_level: str
    excluded_domains: frozenset[str]
    search_tracks: tuple[str, ...] = ()
    english_spoken_level: str = ""


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
_REMOTE = re.compile(r"\b(remote|remotely|worldwide|global|anywhere|work from home|віддалено|віддалений|дистанційно)\b", re.I)
_ENGLISH_ADVANCED = re.compile(r"\b(c1|advanced english|fluent english)\b", re.I)
_ENGLISH_B2 = re.compile(r"\b(b2|upper.intermediate)\b", re.I)
_ENGLISH_LEVEL = re.compile(r"\b(a1|a2|b1|b2|c1|c2)\b", re.I)


def _plain_text(value: str) -> str:
    without_tags = re.sub(r"(?s)<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(without_tags)).strip()


def load_candidate_profile(profile_path: Path) -> CandidateProfile:
    try:
        data = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("Candidate profile unavailable or invalid; run npm run build in Profile/career") from error
    if not isinstance(data, dict) or type(data.get("schemaVersion")) is not int or data["schemaVersion"] != 1:
        raise ValueError("Unsupported candidate profile schemaVersion; expected 1")
    years = data.get("publicExperienceYears")
    if type(years) is not int or not 0 < years < 80:
        raise ValueError("Invalid candidate profile publicExperienceYears")
    for key in ("preferredRole", "homeLocation", "englishPublicLevel", "englishSpokenLevel"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"Invalid candidate profile {key}")
    for key in ("skills", "searchTracks", "excludedDomains"):
        values = data.get(key)
        if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError(f"Invalid candidate profile {key}")
        if key != "excludedDomains" and not values:
            raise ValueError(f"Empty candidate profile {key}")
    if type(data.get("remotePreferred")) is not bool:
        raise ValueError("Invalid candidate profile remotePreferred")
    fingerprint = data.get("sourceFingerprint")
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise ValueError("Invalid candidate profile sourceFingerprint")
    try:
        generated = datetime.fromisoformat(data["generatedAt"].replace("Z", "+00:00"))
        if generated.tzinfo is None:
            raise ValueError("Timezone required")
    except (KeyError, AttributeError, TypeError, ValueError) as error:
        raise ValueError("Invalid candidate profile generatedAt") from error
    aliases = {"swift package manager (spm)": "spm", "modular architecture": "modularization"}
    skills = {value.strip().lower() for value in data["skills"]}
    skills.update(aliases[value] for value in tuple(skills) if value in aliases)
    return CandidateProfile(
        years_ios=years,
        skills=frozenset(skills),
        preferred_role=data["preferredRole"],
        home_location=data["homeLocation"],
        remote_preferred=data["remotePreferred"],
        english_public_level=data["englishPublicLevel"],
        excluded_domains=frozenset(value.strip().lower() for value in data["excludedDomains"]),
        search_tracks=tuple(data["searchTracks"]),
        english_spoken_level=data["englishSpokenLevel"],
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


def _work_mode_score(vacancy: Vacancy) -> tuple[int, list[str], list[str]]:
    location = (vacancy.location or "").strip()
    remote = (vacancy.remote or "").strip()
    if not is_location_eligible(location, remote):
        return 0, [f"work location unavailable from Kyiv: {location}"], ["location mismatch"]
    if _REMOTE.search(remote) or _REMOTE.search(location):
        return 20, ["remote work signal"], []
    if location:
        return 12, ["Kyiv office/hybrid is possible but low preference"], []
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

    work_points, work_reasons, work_blockers = _work_mode_score(vacancy)
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
        if not has_ai_job_details(title, vacancy.description):
            blockers.append("AI job details unavailable")
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
