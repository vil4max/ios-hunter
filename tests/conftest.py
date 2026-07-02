from __future__ import annotations

from pathlib import Path

import pytest

from database.repository import JobRecord, JobRepository
from parser.normalize import Vacancy


@pytest.fixture
def repo(tmp_path: Path) -> JobRepository:
    repository = JobRepository(tmp_path / "test.db")
    yield repository
    repository.close()


def make_vacancy(**overrides) -> Vacancy:
    defaults = {
        "company": "Acme",
        "title": "Senior iOS Developer",
        "url": "https://example.com/job/1",
        "source": "test",
        "location": "Kyiv",
        "remote": "remote",
        "description": "SwiftUI and UIKit experience required",
    }
    defaults.update(overrides)
    return Vacancy(**defaults)


def make_job_record(vacancy: Vacancy, now: str = "2026-07-02T10:00:00+00:00", **overrides) -> JobRecord:
    record = JobRecord(
        id=vacancy.hash,
        company=vacancy.company,
        title=vacancy.title,
        location=vacancy.location,
        remote=vacancy.remote,
        url=vacancy.url,
        source=vacancy.source,
        published_at=None,
        updated_at=now,
        first_seen=now,
        last_seen=now,
        status="open",
        description=vacancy.description,
        hash=vacancy.hash,
    )
    for key, value in overrides.items():
        setattr(record, key, value)
    return record


@pytest.fixture
def sample_profile() -> dict:
    return {
        "skills": ["SwiftUI", "UIKit", "Concurrency", "AI"],
        "skill_priority": ["SwiftUI", "UIKit", "Concurrency", "AI"],
        "remote_preference": "remote",
        "match_threshold": 60,
        "telegram": {"enabled": True},
    }


@pytest.fixture
def sample_skills_map() -> dict[str, list[str]]:
    return {
        "SwiftUI": ["swiftui"],
        "UIKit": ["uikit"],
        "Concurrency": ["async/await"],
        "AI": ["ai", "machine learning"],
    }
