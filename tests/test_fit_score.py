from __future__ import annotations

from analytics.fit_score import CandidateProfile, assess_fit
from parser.normalize import Vacancy


PROFILE = CandidateProfile(
    years_ios=10,
    skills=frozenset({"swift", "swiftui", "uikit", "swift concurrency", "spm", "modularization"}),
    preferred_role="Senior iOS Engineer",
    home_location="Kyiv, Ukraine",
    remote_preferred=True,
    english_public_level="B2",
    excluded_domains=frozenset({"gambling", "dating"}),
)


def test_remote_senior_ios_role_scores_strong() -> None:
    vacancy = Vacancy(
        company="Acme",
        title="Senior iOS Engineer",
        url="https://example.com/jobs/1",
        source="company",
        location="Ukraine",
        remote="remote",
        description="5+ years. Swift, SwiftUI, UIKit, async/await, SPM, modular architecture. English B2.",
    )

    result = assess_fit(vacancy, PROFILE)

    assert result.score >= 78
    assert result.recommendation == "strong"
    assert result.blockers == ()


def test_foreign_onsite_role_is_skipped_even_with_matching_stack() -> None:
    vacancy = Vacancy(
        company="Acme",
        title="Senior iOS Engineer",
        url="https://example.com/jobs/2",
        source="company",
        location="Buenos Aires, Argentina",
        remote="onsite",
        description="Swift, SwiftUI and UIKit. 5+ years.",
    )

    result = assess_fit(vacancy, PROFILE)

    assert result.recommendation == "skip"
    assert "location mismatch" in result.blockers


def test_country_restricted_remote_role_is_skipped() -> None:
    vacancy = Vacancy(
        company="Acme",
        title="Senior iOS Engineer",
        url="https://example.com/jobs/remote-argentina",
        source="company",
        location="Buenos Aires, Argentina",
        remote="remote",
        description="Remote role in Argentina using Swift and UIKit.",
    )

    result = assess_fit(vacancy, PROFILE)

    assert result.recommendation == "skip"
    assert result.blockers == ("location mismatch",)


def test_ukrainian_city_without_country_is_not_a_location_mismatch() -> None:
    for location in ("Lviv", "Kharkiv", "Dnipro", "Odesa"):
        vacancy = Vacancy(
            company="Acme",
            title="Middle iOS Engineer",
            url=f"https://example.com/jobs/{location.lower()}",
            source="company",
            location=location,
            remote="hybrid",
            description="Swift and UIKit.",
        )

        result = assess_fit(vacancy, PROFILE)

        assert "location mismatch" not in result.blockers
        assert f"Ukraine location: {location}" in result.reasons


def test_middle_role_is_eligible_without_seniority_penalty() -> None:
    vacancy = Vacancy(
        company="Acme",
        title="Middle iOS Engineer",
        url="https://example.com/jobs/3",
        source="company",
        location="Ukraine",
        remote="remote",
        description="Swift and UIKit. 3+ years. English B2.",
    )

    result = assess_fit(vacancy, PROFILE)

    assert result.recommendation in {"strong", "review"}
    assert result.blockers == ()
    assert "Middle title is eligible" in result.reasons[0]


def test_middle_plus_role_is_eligible() -> None:
    vacancy = Vacancy(
        company="Acme",
        title="Middle+ iOS Developer",
        url="https://example.com/jobs/middle-plus",
        source="company",
        location="Ukraine",
        remote="remote",
        description="Swift and UIKit. 4+ years.",
    )

    result = assess_fit(vacancy, PROFILE)

    assert result.recommendation != "skip"
    assert result.blockers == ()


def test_junior_role_is_hard_blocked() -> None:
    vacancy = Vacancy(
        company="Acme",
        title="Junior iOS Developer",
        url="https://example.com/jobs/junior",
        source="company",
        location="Ukraine",
        remote="remote",
        description="Swift, UIKit and SwiftUI.",
    )

    result = assess_fit(vacancy, PROFILE)

    assert result.recommendation == "skip"
    assert result.blockers == ("junior-only title",)


def test_english_level_is_informational_and_does_not_change_score() -> None:
    def assessment(description: str):
        vacancy = Vacancy(
            company="Acme",
            title="Senior iOS Engineer",
            url="https://example.com/jobs/english",
            source="company",
            location="Ukraine",
            remote="remote",
            description=f"Swift and UIKit. 5+ years. {description}",
        )
        return assess_fit(vacancy, PROFILE)

    b2 = assessment("English B2 required.")
    c1 = assessment("English C1 required.")
    unspecified = assessment("")

    assert b2.english_requirement == "B2"
    assert c1.english_requirement == "C1"
    assert unspecified.english_requirement == "unspecified"
    assert b2.score == c1.score == unspecified.score
    assert b2.blockers == c1.blockers == unspecified.blockers == ()


def test_excluded_domain_is_skipped() -> None:
    vacancy = Vacancy(
        company="Acme",
        title="Senior iOS Engineer",
        url="https://example.com/jobs/4",
        source="company",
        location="Ukraine",
        remote="remote",
        description="Build a gambling casino product in Swift.",
    )

    result = assess_fit(vacancy, PROFILE)

    assert result.recommendation == "skip"
    assert result.blockers == ("excluded domain: gambling",)
