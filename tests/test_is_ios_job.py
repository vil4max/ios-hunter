from __future__ import annotations

from parser.normalize import is_ios_job


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
