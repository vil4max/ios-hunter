from __future__ import annotations

from pathlib import Path

from database.seen import load_seen, save_seen
from parser.normalize import normalize_many
from scripts.run_pipeline import process_new_vacancies
from tests.conftest import make_vacancy


def test_second_identical_run_sends_nothing(tmp_path: Path, monkeypatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr("scripts.run_pipeline.notify_vacancy", lambda vacancy: sent.append(vacancy.url))

    vacancies = normalize_many(
        [
            {
                "company": "Acme",
                "title": "Senior iOS Engineer",
                "url": "https://example.com/jobs/1",
                "source": "test",
            }
        ]
    )
    seen: dict = {}

    sent_count, marked = process_new_vacancies(vacancies, seen, seed_only=False)
    assert sent_count == 1
    assert marked == 1
    assert len(sent) == 1

    sent_count_2, marked_2 = process_new_vacancies(vacancies, seen, seed_only=False)
    assert sent_count_2 == 0
    assert marked_2 == 0
    assert len(sent) == 1


def test_seed_only_marks_without_sending(monkeypatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr("scripts.run_pipeline.notify_vacancy", lambda vacancy: sent.append(vacancy.url))

    vacancies = [make_vacancy(url="https://example.com/jobs/seed")]
    seen: dict = {}

    sent_count, marked = process_new_vacancies(vacancies, seen, seed_only=True)
    assert sent_count == 0
    assert marked == 1
    assert sent == []
    assert "https://example.com/jobs/seed" in seen


def test_same_url_different_description_does_not_resend(monkeypatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr("scripts.run_pipeline.notify_vacancy", lambda vacancy: sent.append(vacancy.url))

    first = [make_vacancy(url="https://example.com/jobs/2", description="Old")]
    second = [make_vacancy(url="https://example.com/jobs/2", description="Changed requirements")]
    seen: dict = {}

    process_new_vacancies(first, seen, seed_only=False)
    process_new_vacancies(second, seen, seed_only=False)

    assert len(sent) == 1


def test_new_url_sends_once(tmp_path: Path, monkeypatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr("scripts.run_pipeline.notify_vacancy", lambda vacancy: sent.append(vacancy.url))
    path = tmp_path / "seen.json"
    seen = load_seen(path)

    first = [make_vacancy(url="https://example.com/jobs/a")]
    second = [make_vacancy(url="https://example.com/jobs/b", title="iOS Engineer II")]

    process_new_vacancies(first, seen, seed_only=False)
    save_seen(path, seen)
    seen = load_seen(path)
    process_new_vacancies(second, seen, seed_only=False)

    assert sent == ["https://example.com/jobs/a", "https://example.com/jobs/b"]
