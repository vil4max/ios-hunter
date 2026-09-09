from __future__ import annotations

import json

import pytest

from collector.types import CollectResult, SourceResult
from database.seen import mark_seen
from parser.normalize import role_key
from project_sync.github_client import GitHubClient
from project_sync.sync import SyncItemResult, SyncResult
from reporter.collector_health import safe_error
from scripts import run_pipeline
from tests.conftest import make_vacancy


def test_next_city_variant_is_not_new_and_decisions_survive_disabled_seen_gate(monkeypatch):
    first = make_vacancy(url="https://example.com/kyiv")
    other = make_vacancy(url="https://example.com/remote")
    seen = {}
    mark_seen(seen, first)
    assert run_pipeline.select_fresh([other], seen, seen_gate=True) == []
    mark_seen(seen, first, disposition="applied")
    monkeypatch.delenv("CAREER_AGENT_SYNC_ENABLED", raising=False)
    monkeypatch.setenv("CAREER_AGENT_SEEN_GATE", "0")
    monkeypatch.setattr(run_pipeline, "notify_hourly_inbox", lambda *a, **kw: None)
    sent, marked, _, _ = run_pipeline.process_new_vacancies([other], seen, seed_only=False)
    assert (sent, marked) == (0, 0)


def test_github_role_lookup_matches_legacy_titles_and_archived_cards(monkeypatch):
    client = GitHubClient("fake")
    calls = []
    def items(project, **kwargs):
        calls.append(kwargs)
        return [{"id": "old", "isArchived": True, "content": {"title": "Sigma — Senior iOS Engineer (#42)"}}]
    monkeypatch.setattr(client, "list_project_items", items)
    assert client.find_project_item_by_role("project", "Sigma Software", "Senior iOS Engineer") == "old"
    assert calls == [{"include_archived": True}]
    assert role_key("Sigma", "Senior iOS Engineer (#42)") == role_key("Sigma Software", "Senior iOS Engineer")


def test_diagnostics_distinguish_empty_results_filters_and_source_outage(monkeypatch, tmp_path):
    sources = [
        SourceResult("company:broken", "Broken", None, [], "failed", "HTTP 403", 10, 0),
        SourceResult("company:ok", "Working", None, [
            {"company": "Working", "title": "AI Engineer", "url": "https://example.com/ai"},
            {"company": "Working", "title": "Senior iOS Engineer", "url": "https://example.com/ios", "location": "US only remote"},
        ], "healthy", None, 20, 2),
    ]
    report_path = tmp_path / "report.json"
    monkeypatch.setenv("COLLECT_DIAGNOSTICS_PATH", str(report_path))
    monkeypatch.setattr(run_pipeline, "collect_all", lambda: CollectResult(sources))
    _, _, _, health, _ = run_pipeline.collect_vacancies(baseline_path=tmp_path / "baseline.json")
    report = json.loads(report_path.read_text())
    assert not health["company_outage"]
    assert report["rejections"] == {"ai_details_missing": 1, "location": 1}
    assert report["counts"]["inbox_eligible"] == 0
    assert "description" not in report_path.read_text()
    monkeypatch.setattr(run_pipeline, "collect_all", lambda: CollectResult(sources[:1]))
    assert run_pipeline.collect_vacancies(baseline_path=tmp_path / "baseline.json")[3]["company_outage"]


def test_diagnostics_redact_credentials_and_urls(monkeypatch):
    monkeypatch.setenv("CAREER_AGENT_TOKEN", "private-secret")
    assert safe_error("bad private-secret at https://user:password@site.test/?token=other") == "bad [redacted] at [url]"


def test_requested_sync_with_missing_access_fails_before_collection(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.argv", ["run_pipeline.py"])
    monkeypatch.setenv("CAREER_AGENT_SYNC_ENABLED", "1")
    monkeypatch.delenv("CAREER_AGENT_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("COLLECT_DIAGNOSTICS_PATH", str(tmp_path / "report.json"))
    monkeypatch.setattr(run_pipeline, "collect_vacancies", lambda: pytest.fail("Must fail before collection"))
    assert run_pipeline.main() == 1
    assert json.loads((tmp_path / "report.json").read_text())["error"] == "incomplete_sync_configuration"


@pytest.mark.parametrize("sync_failed,outage", [(True, False), (False, True)])
def test_main_fails_on_sync_error_or_total_outage_and_preserves_partial_history(monkeypatch, tmp_path, sync_failed, outage):
    monkeypatch.setattr("sys.argv", ["run_pipeline.py"])
    seen_path = tmp_path / "seen.json"
    report_path = tmp_path / "report.json"
    cursor_path = tmp_path / "cursors.json"
    monkeypatch.setenv("SEEN_PATH", str(seen_path))
    monkeypatch.setenv("JOBS_DB_PATH", str(tmp_path / "absent.db"))
    monkeypatch.setenv("COLLECT_DIAGNOSTICS_PATH", str(report_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    monkeypatch.setattr(run_pipeline, "default_telegram_cursors_path", lambda root: cursor_path)
    monkeypatch.setattr(run_pipeline, "collect_vacancies", lambda: ([], 0, (), {"company_outage": outage, "telegram_cursor_updates": {"chan": 99}}, frozenset()))
    def process(vacancies, seen, **kwargs):
        mark_seen(seen, make_vacancy(), disposition="applied")
        result = SyncResult()
        if sync_failed:
            result.failed.append(SyncItemResult("https://example.com/fail", "Acme", "iOS", failed=True))
        return 0, 1, result, True
    monkeypatch.setattr(run_pipeline, "process_new_vacancies", process)
    assert run_pipeline.main() == 1
    assert json.loads(seen_path.read_text())["https://example.com/job/1"]["disposition"] == "applied"
    assert json.loads(report_path.read_text())["status"] == "failed"
    if sync_failed:
        assert not cursor_path.exists()
