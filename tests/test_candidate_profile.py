from __future__ import annotations

import json
import sys

import pytest

from analytics.fit_score import load_candidate_profile
from scripts import score_inbox


@pytest.fixture
def profile_data():
    return {
        "schemaVersion": 1, "generatedAt": "2026-09-07T00:00:00Z",
        "sourceFingerprint": "a" * 64, "publicExperienceYears": 13,
        "skills": ["Swift", "UIKit", "Swift Package Manager (SPM)", "Modular Architecture"],
        "preferredRole": "Senior iOS Engineer", "searchTracks": ["iOS", "Applied AI"],
        "homeLocation": "Kyiv, Ukraine", "remotePreferred": True,
        "englishPublicLevel": "B2", "englishSpokenLevel": "B1", "excludedDomains": [],
    }


def test_loads_exact_years_skills_and_private_settings(tmp_path, profile_data):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile_data))
    profile = load_candidate_profile(path)
    assert profile.years_ios == 13
    assert {"swift", "uikit", "spm", "modularization"} <= profile.skills
    assert profile.search_tracks == ("iOS", "Applied AI")
    assert profile.english_spoken_level == "B1"


@pytest.mark.parametrize("key,value", [
    ("schemaVersion", 2), ("schemaVersion", True), ("publicExperienceYears", True),
    ("publicExperienceYears", 0), ("publicExperienceYears", "13"), ("skills", []),
    ("skills", "Swift"), ("skills", [None]), ("searchTracks", []),
    ("remotePreferred", "true"), ("generatedAt", "yesterday"),
    ("generatedAt", "2026-09-07"), ("sourceFingerprint", ""),
])
def test_rejects_invalid_contract(tmp_path, profile_data, key, value):
    profile_data[key] = value
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile_data))
    with pytest.raises(ValueError):
        load_candidate_profile(path)


@pytest.mark.parametrize("content", ["{", "[]", "null", "{}"])
def test_rejects_malformed_or_missing_profile(tmp_path, content):
    path = tmp_path / "profile.json"
    with pytest.raises(ValueError):
        load_candidate_profile(path)
    path.write_text(content)
    with pytest.raises(ValueError):
        load_candidate_profile(path)


def test_invalid_profile_fails_before_credentials_or_network(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["score_inbox", "--profile", str(tmp_path / "missing.json")])
    def unexpected(*args, **kwargs):
        pytest.fail("Invalid profile reached a credentials or network operation")
    for name in ("_ensure_env", "load_settings", "GitHubClient", "load_cards_from_github", "collect_all"):
        monkeypatch.setattr(score_inbox, name, unexpected)
    with pytest.raises(SystemExit) as error:
        score_inbox.main()
    assert error.value.code == 2
