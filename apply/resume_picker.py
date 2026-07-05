from __future__ import annotations

from apply.matcher import MatchResult, load_profile


def resume_url(match: MatchResult, profile: dict | None = None) -> str:
    profile = profile or load_profile()
    return resume_url_for_variant(match.resume_version, profile)


def resume_url_for_variant(variant: str, profile: dict | None = None) -> str:
    profile = profile or load_profile()
    cv_urls = profile.get("cv_urls", {})
    return str(cv_urls.get(variant, cv_urls.get("default", "")))


def portfolio_url(profile: dict | None = None) -> str:
    profile = profile or load_profile()
    return str(profile.get("portfolio_url", ""))
