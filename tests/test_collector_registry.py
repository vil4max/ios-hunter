from __future__ import annotations

import json
from collections import Counter

import pytest

from collector import bespoke, companies, djinni, dou, epam, generic, indeed
from collector.types import STATUS_FAILED, SourceResult

_NETWORK_MODULES = (companies, generic, bespoke, epam, djinni, indeed)


class Offline(RuntimeError):
    pass


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every outbound call fail so we exercise each collector's error path."""

    def refuse(*_args, **_kwargs):
        raise Offline("network disabled in tests")

    for module in _NETWORK_MODULES:
        for name in ("fetch_text", "fetch_json", "fetch_text_allowing_bot_wall", "post_form_data"):
            if hasattr(module, name):
                monkeypatch.setattr(module, name, refuse)
    monkeypatch.setattr(dou, "_fetch_text", refuse)
    monkeypatch.setattr(indeed, "_fetch_search_html", refuse)
    monkeypatch.setattr(dou, "collect_dou_ios_rss", lambda: _stub_result("dou-ios-rss", "DOU iOS/macOS"))
    monkeypatch.setattr(companies, "collect_dou_ios_rss", lambda: _stub_result("dou-ios-rss", "DOU iOS/macOS"))
    monkeypatch.setattr(companies, "collect_telegram_channels", lambda: [])


def _stub_result(source_id: str, name: str) -> SourceResult:
    return SourceResult(
        source_id=source_id,
        source_name=name,
        source_url=None,
        jobs=[],
        status="healthy",
        error=None,
        response_ms=0,
        items_scanned=0,
    )


def test_registry_is_not_empty() -> None:
    assert len(companies._python_collectors()) > 50


def test_every_collector_degrades_gracefully_when_the_network_is_down(offline: None) -> None:
    for collector in companies._python_collectors():
        result = collector()

        assert isinstance(result, SourceResult), collector
        assert result.source_name, collector
        assert result.jobs == [], result.source_name
        assert result.items_scanned == 0, result.source_name
        assert result.response_ms >= 0, result.source_name
        if result.source_id.startswith("dou-"):
            continue
        assert result.status == STATUS_FAILED, result.source_name
        assert result.error, result.source_name


def test_source_ids_are_unique_across_the_registry(offline: None) -> None:
    ids = [collector().source_id for collector in companies._python_collectors()]
    duplicates = [source_id for source_id, count in Counter(ids).items() if count > 1]

    assert duplicates == []


def test_companies_registered_more_than_once_keep_one_display_name(offline: None) -> None:
    results = [collector() for collector in companies._python_collectors()]
    by_lowercase: dict[str, set[str]] = {}
    for result in results:
        by_lowercase.setdefault(result.source_name.lower(), set()).add(result.source_name)

    inconsistent = {key: names for key, names in by_lowercase.items() if len(names) > 1}

    assert inconsistent == {}


def test_dou_seed_collectors_are_added_and_deduped(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    seed_path = tmp_path / "dou_companies.json"
    seed_path.write_text(
        json.dumps(
            {
                "updated_at": None,
                "source": "https://jobs.dou.ua/companies/",
                "companies": [
                    {"name": "Alpha", "slug": "alpha"},
                    {"name": "Beta", "slug": "beta", "vacancy_count": 4},
                    {"name": "Gamma", "slug": "gamma", "vacancy_count": 0},
                    {"name": "Skip", "slug": "skip-me", "vacancy_count": 8},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(companies, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(companies, "default_seed_path", lambda _root=None: seed_path)
    monkeypatch.setenv("DOU_SEED_FEED_LIMIT", "all")

    collectors = companies._dou_collectors_from_seed(skip_slugs={"skip-me"})
    monkeypatch.setattr(companies, "collect_dou_company_feed", lambda name, slug: _stub_result(f"company:{slug}@jobs.dou.ua", name))
    results = [collector() for collector in collectors]
    assert {result.source_name for result in results} == {"Alpha", "Beta"}
    assert len(results) == 2


def test_dou_seed_missing_file_adds_no_collectors(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(companies, "default_seed_path", lambda _root=None: tmp_path / "missing.json")
    assert companies._dou_collectors_from_seed() == []

    monkeypatch.setattr(
        companies,
        "_python_collectors",
        lambda: [
            lambda: _stub_result("company:a@a.com", "A"),
            lambda: _stub_result("company:b@b.com", "B"),
        ],
    )
    monkeypatch.setattr(
        companies,
        "collect_telegram_channels",
        lambda: [_stub_result("telegram:chan", "Telegram @chan")],
    )

    result = companies.collect_all(max_workers=2)

    assert {source.source_id for source in result.source_results} == {
        "company:a@a.com",
        "company:b@b.com",
        "telegram:chan",
    }


def test_collect_all_propagates_collector_crashes(monkeypatch: pytest.MonkeyPatch) -> None:
    def crashing() -> SourceResult:
        raise Offline("collector blew up")

    monkeypatch.setattr(companies, "_python_collectors", lambda: [crashing])
    monkeypatch.setattr(companies, "collect_telegram_channels", lambda: [])

    with pytest.raises(Offline):
        companies.collect_all(max_workers=1)
