from __future__ import annotations

from parser.normalize import is_ios_job, is_relevant_job_location


def test_is_ios_job_matches_title() -> None:
    assert is_ios_job("Senior iOS Engineer")
    assert is_ios_job("Swift Developer")
    assert is_ios_job("Objective-C Developer")
    assert is_ios_job("ObjC Engineer")
    assert is_ios_job("SwiftUI / UIKit Engineer")


def test_is_ios_job_matches_description() -> None:
    assert is_ios_job("Mobile Engineer", "Build iOS apps with SwiftUI")


def test_is_ios_job_rejects_unrelated() -> None:
    assert not is_ios_job("Java Backend Engineer")
    assert not is_ios_job("Android Developer", "Kotlin and Jetpack")
    assert not is_ios_job("Admiral Studios SEO Specialist")
    assert not is_ios_job("Manual QA Engineer", "Crypto Casino portfolios and scenarios")
    assert not is_ios_job("UI/UX Designer")


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


def test_is_relevant_job_location_rejects_latam_and_india_only() -> None:
    assert not is_relevant_job_location("Buenos Aires, Argentina")
    assert not is_relevant_job_location("Bengaluru, India")
    assert is_relevant_job_location("Kyiv, Ukraine")
    assert is_relevant_job_location("Remote, Europe")
    assert is_relevant_job_location("Buenos Aires / Remote")
    assert is_relevant_job_location(None)
    assert is_relevant_job_location("")
