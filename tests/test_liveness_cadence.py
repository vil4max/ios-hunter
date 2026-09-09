from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from integrations.vacancy_probe import ProbeResult
from planner.plan import ProjectCard
from project_sync.liveness import find_closed_vacancies

NOW = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)


def card(status="Inbox", **overrides):
    return replace(ProjectCard(
        item_id="item", issue_number=None, title="Senior iOS Engineer", url="https://example.com/job",
        issue_url="", company="Example", source="company", canonical_url="https://example.com/job",
        status=status, priority="", offer_probability="", follow_up=None, applied_at=None,
        created_at=None, updated_at=None,
    ), **overrides)


def opened(url, **kwargs):
    return ProbeResult(url=url, closed=False, skipped=False, http_status=200, reason="open")


def never_probe(*args, **kwargs):
    pytest.fail("Fresh confirmed-open evidence should defer this probe")


@pytest.mark.parametrize("status,hours", [("Inbox", 48), ("Applied", 24), ("Interview", 24)])
def test_positive_cadence_defers_then_probes_at_expiry(tmp_path, status, hours):
    path = tmp_path / "liveness.json"
    first = find_closed_vacancies([card(status)], probe=opened, cache_path=path, now=NOW)
    assert first.checked == 1 and first.deferred == 0
    fresh = find_closed_vacancies([card(status)], probe=never_probe, cache_path=path,
                                  now=NOW + timedelta(hours=hours, seconds=-1))
    assert fresh.deferred == 1 and fresh.checked == 0 and fresh.skipped == 0
    assert fresh.closed == [] and fresh.archived == []
    expired = find_closed_vacancies([card(status)], probe=opened, cache_path=path,
                                    now=NOW + timedelta(hours=hours))
    assert expired.checked == 1 and expired.deferred == 0


def test_status_transition_uses_shorter_active_interval(tmp_path):
    path = tmp_path / "liveness.json"
    find_closed_vacancies([card()], probe=opened, cache_path=path, now=NOW)
    result = find_closed_vacancies([card("Applied")], probe=opened, cache_path=path,
                                   now=NOW + timedelta(hours=25))
    assert result.checked == 1 and result.deferred == 0


@pytest.mark.parametrize("probe_result", [
    ProbeResult(url="", closed=False, skipped=True, http_status=403, reason="bot wall"),
    ProbeResult(url="", closed=False, skipped=True, http_status=200, reason="unknown: no vacancy evidence"),
    ProbeResult(url="", closed=True, skipped=False, http_status=404, reason="http 404"),
    ProbeResult(url="", closed=False, skipped=False, http_status=200, reason="unknown"),
])
def test_non_positive_probe_invalidates_old_open_and_is_not_reused(tmp_path, probe_result):
    path = tmp_path / "liveness.json"
    find_closed_vacancies([card()], probe=opened, cache_path=path, now=NOW)
    result = find_closed_vacancies([card()], probe=lambda *a, **kw: probe_result,
                                   cache_path=path, now=NOW + timedelta(hours=49))
    assert len(result.closed) == int(probe_result.closed)
    assert json.loads(path.read_text())["entries"] == {}
    retry = find_closed_vacancies([card()], probe=opened, cache_path=path, now=NOW + timedelta(hours=50))
    assert retry.checked == 1 and retry.deferred == 0


def test_probe_exception_invalidates_old_open(tmp_path):
    path = tmp_path / "liveness.json"
    find_closed_vacancies([card()], probe=opened, cache_path=path, now=NOW)

    def broken(*args, **kwargs):
        raise RuntimeError("unexpected probe failure")

    with pytest.raises(RuntimeError):
        find_closed_vacancies([card()], probe=broken, cache_path=path, now=NOW + timedelta(hours=49))
    assert json.loads(path.read_text())["entries"] == {}


@pytest.mark.parametrize("change", [{"url": "https://example.com/other"}, {"title": "Applied AI Engineer"}])
def test_cache_key_includes_url_and_title(tmp_path, change):
    path = tmp_path / "liveness.json"
    find_closed_vacancies([card()], probe=opened, cache_path=path, now=NOW)
    result = find_closed_vacancies([card(**change)], probe=opened, cache_path=path, now=NOW)
    assert result.checked == 1 and result.deferred == 0


@pytest.mark.parametrize("raw", ["broken json", "[]", '{"version": 99}', '{"version": 1, "entries": []}'])
def test_malformed_cache_is_cold(tmp_path, raw):
    path = tmp_path / "liveness.json"
    path.write_text(raw)
    assert find_closed_vacancies([card()], probe=opened, cache_path=path, now=NOW).checked == 1


def test_future_and_invalid_positive_entries_are_cold(tmp_path):
    path = tmp_path / "liveness.json"
    find_closed_vacancies([card()], probe=opened, cache_path=path, now=NOW)
    assert find_closed_vacancies([card()], probe=opened, cache_path=path,
                                 now=NOW - timedelta(hours=1)).checked == 1
    data = json.loads(path.read_text())
    record = next(iter(data["entries"].values()))
    record["reason"] = "unknown"
    path.write_text(json.dumps(data))
    assert find_closed_vacancies([card()], probe=opened, cache_path=path, now=NOW).checked == 1


def test_without_path_always_checks_and_cache_never_closes_card():
    for _ in range(2):
        result = find_closed_vacancies([card()], probe=opened, now=NOW)
        assert result.checked == 1 and result.deferred == 0 and result.closed == []


def test_closed_duplicate_invalidates_deferred_positive(tmp_path):
    path = tmp_path / "liveness.json"
    find_closed_vacancies([card()], probe=opened, cache_path=path, now=NOW)
    closed = ProbeResult(url="", closed=True, skipped=False, http_status=404, reason="http 404")
    result = find_closed_vacancies([card(), card("Applied", item_id="second")],
                                   probe=lambda *a, **kw: closed, cache_path=path,
                                   now=NOW + timedelta(hours=25))
    assert result.deferred == 1 and len(result.closed) == 1
    assert json.loads(path.read_text())["entries"] == {}
