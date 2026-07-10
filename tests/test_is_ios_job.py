from __future__ import annotations

from parser.normalize import is_ios_job


def test_is_ios_job_matches_title() -> None:
    assert is_ios_job("Senior iOS Engineer")
    assert is_ios_job("Swift Developer")


def test_is_ios_job_matches_description() -> None:
    assert is_ios_job("Mobile Engineer", "Build iOS apps with SwiftUI")


def test_is_ios_job_rejects_unrelated() -> None:
    assert not is_ios_job("Java Backend Engineer")
    assert not is_ios_job("Android Developer", "Kotlin and Jetpack")
