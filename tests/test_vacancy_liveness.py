from __future__ import annotations

import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

from integrations.vacancy_probe import ProbeResult, probe_vacancy_url, should_skip_url
from planner.plan import ProjectCard
from project_sync.github_client import ProjectField, ProjectMeta
from project_sync.liveness import (
    ClosedVacancyHit,
    LivenessResult,
    archive_closed_vacancies,
    find_closed_vacancies,
)
from reporter.vacancy_liveness import format_vacancy_liveness_report

_KYIV = ZoneInfo("Europe/Kyiv")


def _card(**overrides) -> ProjectCard:
    values = {
        "item_id": "item-1",
        "issue_number": None,
        "title": "iOS Developer",
        "url": "https://example.com/job/1",
        "issue_url": "",
        "company": "Acme",
        "source": "company",
        "canonical_url": "https://example.com/job/1",
        "status": "Applied",
        "priority": "",
        "offer_probability": "",
        "follow_up": None,
        "applied_at": date(2026, 7, 15),
        "created_at": None,
        "updated_at": None,
        "body": "notes",
    }
    values.update(overrides)
    return ProjectCard(**values)


def test_should_skip_telegram_and_private_djinni() -> None:
    assert should_skip_url("https://t.me/itrecruit_ua/1")
    assert should_skip_url("https://djinni.co/my/inbox/1/")
    assert should_skip_url("")
    assert should_skip_url("https://jobs.dou.ua/companies/x/vacancies/1/") is None


def test_probe_marks_http_404_closed(monkeypatch) -> None:
    class FakeResponse:
        status_code = 404
        url = "https://example.com/missing"
        text = "<title>Page Not Found</title>"
        headers: dict[str, str] = {}

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

    result = probe_vacancy_url(
        "https://example.com/missing",
        session=FakeSession(),
    )
    assert result.closed is True
    assert result.reason == "http 404"


def test_probe_skips_cloudflare_challenge_404() -> None:
    class FakeResponse:
        status_code = 404
        url = "https://example.com/job"
        text = (
            "<html><title>Just a moment...</title>"
            "<script>window._cf_chl_opt={}</script>"
            + ("z" * 5500)
            + "</html>"
        )
        headers = {"cf-mitigated": "challenge"}

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

    result = probe_vacancy_url(
        "https://example.com/job",
        session=FakeSession(),
    )
    assert result.closed is False
    assert result.skipped is True
    assert "bot wall" in result.reason


def test_probe_zone3000_html_404_keeps_open_when_api_lists_slug() -> None:
    vacancy_url = (
        "https://zone3000.net/vacancies/"
        "middle-----senior-mobile-ios-developer-in-mobile-system-team---1204-"
    )
    slug = "middle-----senior-mobile-ios-developer-in-mobile-system-team---1204-"

    class HtmlResponse:
        status_code = 404
        url = vacancy_url
        text = "<title>Not Found</title>"
        headers: dict[str, str] = {}

    class ApiResponse:
        status_code = 200
        url = "https://zone3000.net/api/vacancies"
        text = "[]"
        headers: dict[str, str] = {}

        def json(self):
            return [
                {
                    "id": 380,
                    "title": "Middle + / Senior Mobile iOS Developer in Mobile System Team (#1204)",
                    "url": slug,
                    "remote": 1,
                }
            ]

    class FakeSession:
        def get(self, request_url, *args, **kwargs):
            if "api/vacancies" in request_url:
                return ApiResponse()
            return HtmlResponse()

    result = probe_vacancy_url(vacancy_url, session=FakeSession())
    assert result.closed is False
    assert result.skipped is False
    assert result.reason == "open (zone3000 api)"


def test_probe_zone3000_html_404_closed_when_api_missing_slug() -> None:
    vacancy_url = "https://zone3000.net/vacancies/old-ios-role---1-"

    class HtmlResponse:
        status_code = 404
        url = vacancy_url
        text = "<title>Not Found</title>"
        headers: dict[str, str] = {}

    class ApiResponse:
        status_code = 200
        url = "https://zone3000.net/api/vacancies"
        text = "[]"
        headers: dict[str, str] = {}

        def json(self):
            return [{"id": 1, "title": "Support", "url": "support", "remote": 1}]

    class FakeSession:
        def get(self, request_url, *args, **kwargs):
            if "api/vacancies" in request_url:
                return ApiResponse()
            return HtmlResponse()

    result = probe_vacancy_url(vacancy_url, session=FakeSession())
    assert result.closed is True
    assert result.reason == "zone3000 api: vacancy missing"


def test_probe_zone3000_skips_when_api_also_blocked() -> None:
    vacancy_url = "https://zone3000.net/vacancies/some-ios-role---2-"

    class HtmlResponse:
        status_code = 404
        url = vacancy_url
        text = "<title>Not Found</title>"
        headers: dict[str, str] = {}

    class ApiResponse:
        status_code = 403
        url = "https://zone3000.net/api/vacancies"
        text = "<html><title>Just a moment...</title><script>window._cf_chl_opt={}</script></html>"
        headers = {"cf-mitigated": "challenge"}

        def json(self):
            raise ValueError("not json")

    class FakeSession:
        def get(self, request_url, *args, **kwargs):
            if "api/vacancies" in request_url:
                return ApiResponse()
            return HtmlResponse()

    result = probe_vacancy_url(vacancy_url, session=FakeSession())
    assert result.closed is False
    assert result.skipped is True
    assert "zone3000 api blocked" in result.reason


def test_probe_marks_title_mismatch_closed(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200
        url = "https://jobs.dou.ua/companies/x/vacancies/1/"
        text = "<html><h1>Blockchain Developer</h1><body>відгукнутися</body></html>"
        headers: dict[str, str] = {}

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

    result = probe_vacancy_url(
        "https://jobs.dou.ua/companies/x/vacancies/1/",
        card_title="iOS Engineer",
        session=FakeSession(),
    )
    assert result.closed is True
    assert "title mismatch" in result.reason


def test_probe_keeps_matching_ios_title_open() -> None:
    class FakeResponse:
        status_code = 200
        url = "https://jobs.dou.ua/companies/x/vacancies/1/"
        text = "<html><h1>Senior iOS Developer</h1><body>відгукнутися</body></html>"
        headers: dict[str, str] = {}

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

    result = probe_vacancy_url(
        "https://jobs.dou.ua/companies/x/vacancies/1/",
        card_title="Senior iOS Developer",
        session=FakeSession(),
    )
    assert result.closed is False
    assert result.reason == "open"


def test_probe_marks_inactive_dou_vacancy_closed() -> None:
    class FakeResponse:
        status_code = 200
        url = "https://jobs.dou.ua/companies/x/vacancies/1/"
        text = "<html><h1>Senior iOS Developer (вакансія неактивна)</h1></html>"
        headers: dict[str, str] = {}

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

    result = probe_vacancy_url(FakeResponse.url, session=FakeSession())
    assert result.closed is True
    assert "вакансія неактивна" in result.reason


def test_probe_marks_closed_nix_vacancy_closed() -> None:
    class FakeResponse:
        status_code = 200
        url = "https://careers.n-ix.com/jobs/old-ios-role/"
        text = "<html><h1>Senior iOS Engineer</h1>The vacancy is already closed.</html>"
        headers: dict[str, str] = {}

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

    result = probe_vacancy_url(FakeResponse.url, session=FakeSession())
    assert result.closed is True
    assert "vacancy is already closed" in result.reason


def test_probe_keeps_active_next_data_job_open_despite_footer_marker() -> None:
    payload = {
        "props": {
            "pageProps": {
                "job": {"name": "Senior iOS Developer", "is_expired": False},
            }
        }
    }

    class FakeResponse:
        status_code = 200
        url = "https://careers.epam.com/en/vacancy/ios"
        text = (
            '<html><h1>Senior iOS Developer</h1><script id="__NEXT_DATA__">'
            + json.dumps(payload)
            + "</script><footer>Page not found</footer></html>"
        )
        headers: dict[str, str] = {}

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

    result = probe_vacancy_url(
        FakeResponse.url,
        card_title="Senior iOS Developer",
        session=FakeSession(),
    )
    assert result.closed is False
    assert result.reason == "open"


def test_probe_marks_expired_next_data_job_closed_without_text_marker() -> None:
    payload = {
        "props": {
            "pageProps": {
                "job": {"name": "Senior iOS Developer", "is_expired": True},
            }
        }
    }

    class FakeResponse:
        status_code = 200
        url = "https://careers.epam.com/en/vacancy/expired-ios"
        text = (
            '<html><h1>Senior iOS Developer</h1><script id="__NEXT_DATA__">'
            + json.dumps(payload)
            + "</script></html>"
        )
        headers: dict[str, str] = {}

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

    result = probe_vacancy_url(
        FakeResponse.url,
        card_title="Senior iOS Developer",
        session=FakeSession(),
    )
    assert result.closed is True
    assert result.reason == "structured job expired"


def test_find_closed_vacancies_uses_probe() -> None:
    cards = [
        _card(item_id="a", status="Applied", url="https://example.com/a"),
        _card(item_id="b", status="Archived", url="https://example.com/b"),
        _card(item_id="c", status="Replied", url="https://t.me/x/1", title="TG"),
    ]

    def fake_probe(url: str, card_title: str = ""):
        if "t.me" in url:
            return ProbeResult(url=url, closed=False, skipped=True, http_status=None, reason="skip")
        if url.endswith("/a"):
            return ProbeResult(url=url, closed=True, skipped=False, http_status=404, reason="http 404")
        return ProbeResult(url=url, closed=False, skipped=False, http_status=200, reason="open")

    result = find_closed_vacancies(cards, probe=fake_probe)
    assert result.checked == 1
    assert result.skipped == 1
    assert len(result.closed) == 1
    assert result.closed[0].card.item_id == "a"


def test_archive_closed_vacancies_sets_fields() -> None:
    calls: list[tuple] = []

    class FakeClient:
        def set_single_select_field(self, **kwargs):
            calls.append(("select", kwargs))

        def draft_issue_id_for_item(self, project_id, item_id):
            return "draft-1"

        def update_draft_issue(self, draft_id, **kwargs):
            calls.append(("draft", draft_id, kwargs))

        def archive_project_item(self, project_id, item_id):
            calls.append(("archive", project_id, item_id))

    meta = ProjectMeta(
        project_id="proj",
        status_field=ProjectField(
            id="status",
            name="Status",
            kind="single_select",
            options={"Applied": "opt-applied", "Archived": "opt-arch"},
        ),
        fields_by_name={
            "Close Reason": ProjectField(
                id="close",
                name="Close Reason",
                kind="single_select",
                options={"Role closed": "opt-role"},
            ),
            "Closed Stage": ProjectField(
                id="stage",
                name="Closed Stage",
                kind="single_select",
                options={"Applied": "opt-stage-applied"},
            ),
        },
    )
    hit = ClosedVacancyHit(
        card=_card(),
        probe=ProbeResult(
            url="https://example.com/job/1",
            closed=True,
            skipped=False,
            http_status=404,
            reason="http 404",
        ),
    )
    archived = archive_closed_vacancies(
        FakeClient(),
        hits=[hit],
        today=date(2026, 7, 28),
        meta=meta,
    )
    assert len(archived) == 1
    select_calls = [c for c in calls if c[0] == "select"]
    assert any(c[1]["option_id"] == "opt-role" for c in select_calls)
    assert any(c[1]["option_id"] == "opt-stage-applied" for c in select_calls)
    draft_calls = [c for c in calls if c[0] == "draft"]
    assert "Role closed" in draft_calls[0][2]["body"]
    assert ("archive", "proj", "item-1") in calls


def test_format_liveness_report_empty_and_archived() -> None:
    now = datetime(2026, 7, 28, 7, 0, tzinfo=_KYIV)
    empty = format_vacancy_liveness_report(
        LivenessResult(checked=5, skipped=2),
        board_url="https://github.com/users/x/projects/3",
        now=now,
    )
    assert empty == "✅ Отправлено в архив: 0\n\n🕐 2026-07-28 07:00"

    hit = ClosedVacancyHit(
        card=_card(company="Andersen", title="iOS Developer", url="https://example.com/x"),
        probe=ProbeResult(
            url="https://example.com/x",
            closed=True,
            skipped=False,
            http_status=404,
            reason="http 404",
        ),
    )
    message = format_vacancy_liveness_report(
        LivenessResult(checked=4, skipped=1, archived=[hit]),
        board_url="https://github.com/users/x/projects/3",
        now=now,
    )
    assert message.startswith("🗂️ Отправлено в архив: 1")
    assert "1. Andersen — iOS Developer" in message
    assert "└ http 404" in message
    assert "🔗 https://example.com/x" in message
    assert message.endswith("🕐 2026-07-28 07:00")
    assert "Проверено:" not in message
    assert "пропущено" not in message


def test_format_liveness_report_dry_run_closed_not_archived() -> None:
    now = datetime(2026, 7, 28, 7, 0, tzinfo=_KYIV)
    hit = ClosedVacancyHit(
        card=_card(company="Acme", title="Swift Engineer"),
        probe=ProbeResult(
            url="https://example.com/y",
            closed=True,
            skipped=False,
            http_status=410,
            reason="http 410",
        ),
    )
    message = format_vacancy_liveness_report(
        LivenessResult(checked=1, skipped=0, closed=[hit], archived=[]),
        now=now,
    )
    assert message.startswith("⚠️ Найдено закрытых: 1")
    assert "1. Acme — Swift Engineer" in message
    assert message.endswith("🕐 2026-07-28 07:00")
