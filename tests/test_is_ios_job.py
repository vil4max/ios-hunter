from __future__ import annotations

from parser.normalize import (
    canonical_company,
    is_ios_job,
    is_relevant_job_location,
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
    assert not is_ios_job("Middle C++ Developer (Windows/macOS)")
    assert not is_ios_job("C++ Developer Windows/macOS")
    assert not is_ios_job("Senior CPP Engineer (Windows / Mac OS)")
    assert is_ios_job("Principal macOS Platform Engineer")
    assert is_ios_job("macOS Developer (Swift / AppKit)")
    assert is_ios_job("iOS/C++ Engineer")


def test_is_ios_job_rejects_qa_and_test_noise() -> None:
    assert not is_ios_job("Mobile Automation QA Engineer (iOS & Android)")
    assert not is_ios_job("Senior iOS Test Engineer")
    assert not is_ios_job("iOS SDET")
    assert not is_ios_job("TPM (Java/Android/iOS)")
    assert not is_ios_job("Test Automation Engineer iOS")
    assert not is_ios_job("Lead KMM Engineer – KMM, Android, iOS")
    assert not is_ios_job("Kotlin Multiplatform Engineer (iOS)")
    assert is_ios_job("Senior iOS Engineer")
    assert is_ios_job("Swift Developer")


def test_is_ios_job_rejects_igaming_and_gambling() -> None:
    assert not is_ios_job("Team Lead Swift", "Affiliate Marketing, розвиваємо iGaming-продукти")
    assert not is_ios_job("Senior iOS Engineer", "Online casino and sportsbook mobile apps")
    assert not is_ios_job("iOS Developer", "Gambling / betting platform for EU markets")
    assert not is_ios_job("Swift Developer", "Букмекерська компанія шукає iOS")
    assert not is_ios_job("Lead iOS", "Казино product, SwiftUI")
    assert is_ios_job("Senior iOS Engineer", "Fintech payments and crypto exchange")
    assert is_ios_job("Team Lead Swift", "Health & fitness subscription apps")


def test_is_ios_job_rejects_flutter_and_reverse_engineer() -> None:
    assert not is_ios_job("Senior Flutter Developer")
    assert not is_ios_job("Вакансия: Senior Flutter Developer")
    assert not is_ios_job("iOS Reverse Engineer - 1 Task")
    assert is_ios_job("Senior iOS Engineer (Flutter is a plus)")


def test_is_ios_job_rejects_react_native_and_keeps_ios_plus_rn() -> None:
    assert not is_ios_job("React Native Developer (iOS/Android)")
    assert not is_ios_job("Senior RN Engineer")
    assert not is_ios_job("Xamarin Developer")
    assert not is_ios_job("Mobile Engineer", "React Native for iOS and Android")
    assert is_ios_job("Senior iOS Engineer (React Native is a plus)")


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


def test_normalize_raw_drops_junior_and_non_ua_title_geo() -> None:
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
    assert kazakh is None
    assert keep is not None


def test_canonical_company_aliases_nix() -> None:
    assert canonical_company("N-iX") == canonical_company("NIX")
    assert canonical_company("N i X") == "n-ix"
    assert role_key("N-iX", "Lead iOS Engineer") == role_key("NIX", "Lead iOS Engineer")


def test_is_relevant_job_location_ukraine_and_global_remote() -> None:
    assert is_relevant_job_location("Kyiv, Ukraine")
    assert is_relevant_job_location("Ukraine")
    assert is_relevant_job_location("Remote, Europe")
    assert is_relevant_job_location("Worldwide")
    assert is_relevant_job_location("Remote")
    assert is_relevant_job_location(None)
    assert is_relevant_job_location("")


def test_is_relevant_job_location_rejects_non_ua_geo() -> None:
    assert not is_relevant_job_location("Buenos Aires, Argentina")
    assert not is_relevant_job_location("Buenos Aires / Remote")
    assert not is_relevant_job_location("Argentina / Chile / Colombia / Mexico")
    assert not is_relevant_job_location("Hybrid, Budapest, Hungary")
    assert not is_relevant_job_location("Bengaluru, India")
    assert not is_relevant_job_location("Kuala Lumpur, Malaysia")
    assert not is_relevant_job_location("Cairo, Egypt")
    assert not is_relevant_job_location("Austin, USA")
    assert not is_relevant_job_location("Poland, Remote")
    assert not is_relevant_job_location("Львів, Краків (Польща), віддалено")


def test_is_relevant_job_location_falls_back_to_title_and_description() -> None:
    assert is_relevant_job_location(None, "Senior iOS Engineer · Kyiv, Ukraine")
    assert is_relevant_job_location("", "Worldwide remote Swift team")
    assert not is_relevant_job_location(None, "iOS Developer (Swift) in Kazakhstan")
    assert not is_relevant_job_location("", "Office in Bengaluru, India")
    assert is_relevant_job_location(None, "Senior iOS Engineer, remote")
