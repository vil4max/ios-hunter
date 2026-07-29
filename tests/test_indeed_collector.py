from __future__ import annotations

import pytest

from collector import indeed


def _item(**overrides):
    base = {
        "jobkey": "abc123def4567890",
        "title": "Senior iOS Engineer",
        "company": "Acme",
        "formattedLocation": "Київ",
        "snippet": "<b>Swift</b> and UIKit",
        "remoteLocation": None,
        "isJobRemote": False,
    }
    base.update(overrides)
    return base


def _html_with_results(results: list[dict]) -> str:
    import json

    payload = {
        "metaData": {
            "mosaicProviderJobCardsModel": {
                "pageNumber": 1,
                "results": results,
            }
        }
    }
    return (
        "<html><body><script>\n"
        f'window.mosaic.providerData["mosaic-provider-jobcards"]={json.dumps(payload, ensure_ascii=False)};\n'
        "</script></body></html>"
    )


def test_parse_jobcards_html_reads_results() -> None:
    html = _html_with_results([_item(), _item(jobkey="other", title="QA Engineer (iOS)")])
    parsed = indeed.parse_jobcards_html(html)
    assert len(parsed) == 2
    assert parsed[0]["jobkey"] == "abc123def4567890"


def test_job_from_item_builds_viewjob_url() -> None:
    job = indeed._job_from_item(_item())
    assert job is not None
    assert job["url"] == "https://ua.indeed.com/viewjob?jk=abc123def4567890"
    assert job["source"] == "indeed"
    assert job["source_job_id"] == "abc123def4567890"
    assert job["company"] == "Acme"
    assert job["description"] == "Swift and UIKit"
    assert job["remote"] == "unknown"


def test_job_from_item_maps_remote_location() -> None:
    job = indeed._job_from_item(
        _item(formattedLocation="Дистанційно", remoteLocation=True, title="iOS Developer")
    )
    assert job is not None
    assert job["remote"] == "remote"


def test_job_from_item_rejects_qa_titles() -> None:
    assert indeed._job_from_item(_item(title="QA Engineer (iOS / Data Validation)")) is None


def test_job_from_item_rejects_non_ua_geo() -> None:
    assert indeed._job_from_item(_item(formattedLocation="Buenos Aires, Argentina")) is None


def test_collect_indeed_filters_and_dedupes(monkeypatch: pytest.MonkeyPatch) -> None:
    html = _html_with_results(
        [
            _item(jobkey="1", title="Senior iOS Engineer"),
            _item(jobkey="1", title="Senior iOS Engineer"),
            _item(jobkey="2", title="QA Engineer (iOS)"),
            _item(jobkey="3", title="Backend Engineer", snippet="Java Spring"),
            _item(jobkey="4", title="Middle iOS Developer", company="N-iX", formattedLocation="Украина"),
        ]
    )
    monkeypatch.setattr(indeed, "_fetch_search_html", lambda: html)

    result = indeed.collect_indeed()

    assert result.status == "healthy"
    assert result.source_id == "indeed"
    assert result.items_scanned == 5
    assert sorted(job["source_job_id"] for job in result.jobs) == ["1", "4"]


def test_collect_indeed_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        indeed,
        "_fetch_search_html",
        lambda: (_ for _ in ()).throw(RuntimeError("blocked")),
    )

    result = indeed.collect_indeed()

    assert result.status == "failed"
    assert "blocked" in (result.error or "")
