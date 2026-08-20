from __future__ import annotations

from pathlib import Path

import pytest

from collector.types import CollectResult, SourceResult
from database.source_health import load_baseline, save_baseline
from scripts import run_pipeline


def _source(
    source_id: str,
    name: str,
    *,
    scanned: int,
    jobs: list[dict] | None = None,
    status: str = "healthy",
    error: str | None = None,
) -> SourceResult:
    return SourceResult(
        source_id=source_id,
        source_name=name,
        source_url="https://acme.com",
        jobs=jobs or [],
        status=status,
        error=error,
        response_ms=5,
        items_scanned=scanned,
    )


def _job(url: str, company: str = "Acme") -> dict:
    return {"company": company, "title": "Senior iOS Engineer", "url": url, "source": "company"}


def test_collect_vacancies_marks_previously_working_source_as_degraded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    baseline_path = tmp_path / "baseline.json"
    save_baseline(baseline_path, {"company:acme@acme.com": {"best_scanned": 40}})
    monkeypatch.setattr(
        run_pipeline,
        "collect_all",
        lambda: CollectResult(source_results=[_source("company:acme@acme.com", "Acme", scanned=0)]),
    )

    _, _, failed, health, purgeable = run_pipeline.collect_vacancies(baseline_path=baseline_path)

    assert failed == ()
    assert health["degraded_source_names"] == ("Acme",)
    assert health["sites_ok"] == 0
    assert purgeable == frozenset()
    assert "Source degraded (parsed 0 items): Acme" in capsys.readouterr().err


def test_collect_vacancies_does_not_flag_a_source_without_history(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        run_pipeline,
        "collect_all",
        lambda: CollectResult(source_results=[_source("company:new@new.com", "New", scanned=0)]),
    )

    _, _, _, health, _ = run_pipeline.collect_vacancies(baseline_path=tmp_path / "baseline.json")

    assert health["degraded_source_names"] == ()
    assert health["sites_ok"] == 1


def test_collect_vacancies_only_purges_sources_that_actually_parsed_something(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        run_pipeline,
        "collect_all",
        lambda: CollectResult(
            source_results=[
                _source("company:working@a.com", "Working", scanned=9, jobs=[_job("https://a.com/1")]),
                _source("company:blind@b.com", "Blind", scanned=0),
                _source("dou-top50", "DOU Top 50", scanned=3, jobs=[_job("https://dou.ua/1", "DOU Top 50")]),
                _source("telegram:chan", "Telegram @chan", scanned=4),
            ]
        ),
    )

    _, _, _, _, purgeable = run_pipeline.collect_vacancies(baseline_path=tmp_path / "baseline.json")

    assert purgeable == frozenset({"Working", "DOU Top 50"})


def test_collect_vacancies_persists_the_baseline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    baseline_path = tmp_path / "baseline.json"
    monkeypatch.setattr(
        run_pipeline,
        "collect_all",
        lambda: CollectResult(source_results=[_source("company:acme@acme.com", "Acme", scanned=17)]),
    )

    run_pipeline.collect_vacancies(baseline_path=baseline_path)

    assert load_baseline(baseline_path)["company:acme@acme.com"]["best_scanned"] == 17


def test_collect_vacancies_reports_failed_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        run_pipeline,
        "collect_all",
        lambda: CollectResult(
            source_results=[
                _source("company:down@a.com", "Down", scanned=0, status="failed", error="403"),
            ]
        ),
    )

    _, _, failed, health, _ = run_pipeline.collect_vacancies(baseline_path=tmp_path / "baseline.json")

    assert failed == ("Down",)
    assert health["sites_total"] == 1
    assert "Source failed: Down: 403" in capsys.readouterr().err


def test_collect_vacancies_dedupes_across_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        run_pipeline,
        "collect_all",
        lambda: CollectResult(
            source_results=[
                _source("company:a@a.com", "Acme", scanned=1, jobs=[_job("https://a.com/jobs/1")]),
                _source(
                    "company:b@b.com",
                    "Acme",
                    scanned=1,
                    jobs=[_job("https://a.com/jobs/1?utm_source=x")],
                ),
            ]
        ),
    )

    vacancies, removed, _, _, _ = run_pipeline.collect_vacancies(baseline_path=tmp_path / "baseline.json")

    assert len(vacancies) == 1
    assert removed == 1


def test_summarize_counts_telegram_separately() -> None:
    results = [
        _source("company:a@a.com", "Acme", scanned=1),
        _source("company:b@b.com", "Broken", scanned=0, status="failed", error="boom"),
        _source("company:c@c.com", "Silent", scanned=0, status="degraded"),
        _source("telegram:one", "Telegram @one", scanned=2),
        _source("telegram:two", "Telegram @two", scanned=0, error="TELEGRAM_SESSION not set"),
        _source("telegram:three", "Telegram @three", scanned=0, status="failed", error="auth"),
    ]

    failed, health = run_pipeline.summarize_source_checks(results)

    assert failed == ("Broken", "Telegram @three")
    assert health["sites_ok"] == 1
    assert health["sites_total"] == 3
    assert health["degraded_source_names"] == ("Silent",)
    assert health["telegram_ok"] == 1
    assert health["telegram_total"] == 3
    assert health["telegram_skipped"] == 1
    assert health["telegram_ok_names"] == ("one",)


def test_telegram_channel_label_falls_back_to_source_name() -> None:
    assert run_pipeline._telegram_channel_label(_source("telegram:chan", "whatever", scanned=0)) == "chan"
    assert (
        run_pipeline._telegram_channel_label(_source("other", "Telegram @beta", scanned=0)) == "beta"
    )
    assert run_pipeline._telegram_channel_label(_source("other", "Plain", scanned=0)) == "Plain"
