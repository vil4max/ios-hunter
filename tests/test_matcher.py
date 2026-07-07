from __future__ import annotations

from apply.matcher import detect_skills, match_job, pick_resume_version
from tests.conftest import make_job_record, make_vacancy


def test_match_job_scores_strong_ios_overlap(sample_profile, sample_skills_map) -> None:
    vacancy = make_vacancy(description="SwiftUI, UIKit, async/await, and AI experience")
    job = make_job_record(vacancy)

    result = match_job(job, profile=sample_profile, skills_map=sample_skills_map)

    assert result.score >= 60
    assert "SwiftUI" in result.strong
    assert "UIKit" in result.strong
    assert result.remote_ok is True


def test_match_job_penalizes_onsite_for_remote_preference(sample_profile, sample_skills_map) -> None:
    vacancy = make_vacancy(remote="onsite", description="SwiftUI and UIKit")
    job = make_job_record(vacancy)

    result = match_job(job, profile=sample_profile, skills_map=sample_skills_map)

    assert result.remote_ok is False
    assert result.score < 80


def test_detect_skills_finds_keywords(sample_skills_map) -> None:
    found = detect_skills("Looking for SwiftUI and machine learning skills", sample_skills_map)

    assert "SwiftUI" in found
    assert "AI" in found


def test_pick_resume_version_prefers_ai() -> None:
    assert pick_resume_version(["SwiftUI", "AI"]) == "ai"
    assert pick_resume_version(["SwiftUI", "SDK"]) == "sdk"
    assert pick_resume_version(["SwiftUI"]) == "product"
