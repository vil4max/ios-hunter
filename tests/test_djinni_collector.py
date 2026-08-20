from __future__ import annotations

import pytest

from collector import djinni


def _item(**overrides):
    base = {
        "id": 1,
        "title": "Senior iOS Engineer",
        "slug": "1-senior-ios-engineer",
        "company_name": "Acme",
        "long_description": "Swift and UIKit",
        "location": "Kyiv",
        "work_format": "Full Remote",
        "is_ukraine_only": False,
        "published": "2026-07-27T10:00:00",
    }
    base.update(overrides)
    return base


def test_map_remote() -> None:
    assert djinni._map_remote("Full Remote") == "remote"
    assert djinni._map_remote("Remote, Hybrid Remote") == "hybrid"
    assert djinni._map_remote("Office, Hybrid Remote") == "hybrid"
    assert djinni._map_remote("Office") == "onsite"
    assert djinni._map_remote("") == "unknown"


def test_job_from_item_builds_djinni_url() -> None:
    job = djinni._job_from_item(_item())

    assert job is not None
    assert job["url"] == "https://djinni.co/jobs/1-senior-ios-engineer/"
    assert job["source"] == "djinni"
    assert job["company"] == "Acme"
    assert job["remote"] == "remote"
    assert job["location"] == "Kyiv"


def test_job_from_item_rejects_non_ios_titles() -> None:
    assert djinni._job_from_item(_item(title="Manual QA", long_description="test cases")) is None


def test_job_from_item_keeps_non_ua_geo() -> None:
    job = djinni._job_from_item(
        _item(location="Buenos Aires, Argentina", is_ukraine_only=False)
    )

    assert job is not None
    assert job["location"] == "Buenos Aires, Argentina"


def test_job_from_item_accepts_ukraine_only_flag() -> None:
    job = djinni._job_from_item(_item(location="", is_ukraine_only=True, work_format="Office"))

    assert job is not None
    assert "Ukraine" in (job["location"] or "")


def test_fetch_category_jobs_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        0: {"count": 4, "limit": 2, "results": [_item(id=1), _item(id=2, slug="2-x")]},
        2: {"count": 4, "limit": 2, "results": [_item(id=3, slug="3-x"), _item(id=4, slug="4-x")]},
    }

    def fake_fetch(url: str, **_kwargs):
        if "offset=2" in url:
            return pages[2]
        return pages[0]

    monkeypatch.setattr(djinni, "fetch_json", fake_fetch)

    jobs = djinni.fetch_category_jobs("iOS")

    assert [job["id"] for job in jobs] == [1, 2, 3, 4]


def test_collect_djinni_merges_ios_and_swift(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_category(category: str):
        if category == "iOS":
            return [
                _item(id=1),
                _item(id=2, title="iOS Farmer", slug="2-farmer", long_description="farming"),
                _item(id=3, title="Backend Engineer", slug="3-be", long_description="Java Spring"),
            ]
        return [
            _item(id=1, title="Lead iOS Engineer", slug="1-dup"),
            _item(id=9, title="macOS Developer (Swift / AppKit)", slug="9-macos", location=""),
        ]

    monkeypatch.setattr(djinni, "fetch_category_jobs", fake_category)

    result = djinni.collect_djinni()

    assert result.status == "healthy"
    assert result.source_id == "djinni"
    assert result.items_scanned == 5
    titles = sorted(job["title"] for job in result.jobs)
    assert "Senior iOS Engineer" in titles
    assert "macOS Developer (Swift / AppKit)" in titles
    assert "Backend Engineer" not in titles


def test_collect_djinni_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        djinni,
        "fetch_category_jobs",
        lambda category: (_ for _ in ()).throw(RuntimeError("api down")),
    )

    result = djinni.collect_djinni()

    assert result.status == "failed"
    assert "api down" in (result.error or "")
