from __future__ import annotations

from parser.normalize import (
    Vacancy,
    canonical_company,
    is_inbox_candidate,
    is_ios_job,
    is_primary_ios_role,
    is_target_location,
    is_target_level,
    normalize_raw,
    role_key,
)


def test_is_ios_job_matches_title() -> None:
    assert is_ios_job("Senior iOS Engineer")
    assert is_ios_job("Swift Developer")
    assert is_ios_job("Objective-C Developer")
    assert is_ios_job("ObjC Engineer")
    assert is_ios_job("SwiftUI / UIKit Engineer")
    assert is_ios_job("Principal macOS Platform Engineer")
    assert is_ios_job("macOS Developer (Swift / AppKit)")


def test_is_ios_job_matches_description() -> None:
    assert is_ios_job("Mobile Engineer", "Build iOS apps with SwiftUI")


def test_is_ios_job_rejects_unrelated() -> None:
    assert not is_ios_job("Java Backend Engineer")
    assert not is_ios_job("Android Developer", "Kotlin and Jetpack")
    assert not is_ios_job("Admiral Studios SEO Specialist")
    assert not is_ios_job("Manual QA Engineer", "Crypto Casino portfolios and scenarios")
    assert not is_ios_job("UI/UX Designer")
    assert is_ios_job("Middle C++ Developer (Windows/macOS)")
    assert is_ios_job("C++ Developer Windows/macOS")
    assert is_ios_job("Senior CPP Engineer (Windows / Mac OS)")
    assert is_ios_job("Principal macOS Platform Engineer")
    assert is_ios_job("macOS Developer (Swift / AppKit)")
    assert is_ios_job("iOS/C++ Engineer")


def test_is_ios_job_rejects_qa_and_test_noise() -> None:
    assert not is_ios_job("Mobile Automation QA Engineer (iOS & Android)")
    assert not is_ios_job("Senior iOS Test Engineer")
    assert not is_ios_job("iOS SDET")
    assert not is_ios_job("TPM (Java/Android/iOS)")
    assert not is_ios_job("Test Automation Engineer iOS")
    assert is_ios_job("Lead KMM Engineer – KMM, Android, iOS")
    assert is_ios_job("Kotlin Multiplatform Engineer (iOS)")
    assert is_ios_job("Senior iOS Engineer")
    assert is_ios_job("Swift Developer")


def test_is_ios_job_does_not_filter_by_product_domain() -> None:
    assert is_ios_job("Team Lead Swift", "Affiliate Marketing, розвиваємо iGaming-продукти")
    assert is_ios_job("Senior iOS Engineer", "Online casino and sportsbook mobile apps")
    assert is_ios_job("iOS Developer", "Gambling / betting platform for EU markets")


def test_is_ios_job_requires_an_apple_signal_for_cross_platform_titles() -> None:
    assert not is_ios_job("Senior Flutter Developer")
    assert not is_ios_job("Вакансия: Senior Flutter Developer")
    assert is_ios_job("iOS Reverse Engineer - 1 Task")
    assert is_ios_job("Senior iOS Engineer (Flutter is a plus)")


def test_is_ios_job_keeps_mobile_roles_with_ios_in_cross_platform_description() -> None:
    assert is_ios_job("React Native Developer (iOS/Android)")
    assert not is_ios_job("Senior RN Engineer")
    assert not is_ios_job("Xamarin Developer")
    assert is_ios_job("Mobile Engineer", "React Native for iOS and Android")
    assert is_ios_job("Senior iOS Engineer (React Native is a plus)")
    assert is_ios_job("Kotlin Multiplatform Engineer (iOS)")


def test_is_ios_job_uses_description_only_for_mobile_roles() -> None:
    assert is_ios_job("Mobile Engineer", "Build iOS apps with SwiftUI")
    assert is_ios_job("Senior Software Engineer", "Native iOS, Swift, UIKit")
    assert not is_ios_job("Java Backend Engineer", "Our product also has an iOS app")
    assert not is_ios_job("Data Analyst", "Dashboards for the iOS store listing")


def test_is_target_level_drops_junior_and_intern() -> None:
    assert not is_target_level("Trainee iOS Software Developer")
    assert not is_target_level("Junior iOS Developer")
    assert not is_target_level("iOS Intern")
    assert is_target_level("Middle iOS Engineer")
    assert is_target_level("Senior iOS Engineer")
    assert is_target_level("Junior / Senior iOS Engineer")


def test_normalize_raw_drops_junior_but_keeps_non_ua_location() -> None:
    junior = normalize_raw(
        {
            "company": "Acme",
            "title": "Trainee iOS Software Developer",
            "url": "https://example.com/jobs/1",
            "source": "djinni",
        }
    )
    kazakh = normalize_raw(
        {
            "company": "Andersen",
            "title": "iOS Developer (Swift) in Kazakhstan",
            "url": "https://example.com/jobs/2",
            "source": "company",
        }
    )
    keep = normalize_raw(
        {
            "company": "Acme",
            "title": "Senior iOS Engineer",
            "url": "https://example.com/jobs/3",
            "source": "company",
        }
    )
    assert junior is None
    assert kazakh is not None
    assert keep is not None


def test_inbox_candidate_rejects_cross_platform_titles() -> None:
    assert not is_primary_ios_role("Middle Mobile iOS/Android Engineer")
    assert not is_primary_ios_role("iOS Developer with Android")
    assert not is_primary_ios_role("React Native Developer (iOS/Android)")
    assert is_primary_ios_role("Senior iOS Engineer (Flutter is a plus)")


def test_target_location_rejects_country_restricted_remote_roles() -> None:
    assert not is_target_location("Cordoba, Buenos Aires")
    assert not is_target_location("Basking Ridge NJ, United States")
    assert is_target_location("Ukraine")
    assert is_target_location("Eastern Europe")
    assert is_target_location(None)


def test_inbox_candidate_requires_primary_ios_and_target_location() -> None:
    vacancy = Vacancy(
        company="Avenga",
        title="Senior iOS Engineer",
        url="https://example.com/jobs/ios",
        source="company",
        location="Buenos Aires",
        remote="remote",
    )

    assert not is_inbox_candidate(vacancy)


def test_canonical_company_aliases_nix() -> None:
    assert canonical_company("N-iX") == canonical_company("NIX")
    assert canonical_company("N i X") == "n-ix"
    assert role_key("N-iX", "Lead iOS Engineer") == role_key("NIX", "Lead iOS Engineer")
