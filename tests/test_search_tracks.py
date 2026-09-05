import pytest

from analytics.fit_score import CandidateProfile, assess_fit
from collector import bespoke
from collector.company_watchlist import _add_candidate
from collector.epam import discover_ios_vacancy_urls
from config.search_tracks import AI_TARGET_TITLES
from parser.normalize import Vacancy, ai_negative_signals, is_target_job, normalize_raw


@pytest.mark.parametrize("title", AI_TARGET_TITLES + ("Senior Software Engineer, AI", "Engineer - AI Solutions"))
def test_ai_title_variants_reach_normalization(title):
    assert is_target_job(title)
    assert normalize_raw(dict(title=title, company="Acme", url="https://example.com/jobs/1"))


@pytest.mark.parametrize("title", ("Data Scientist", "ML Engineer", "Computer Vision Engineer", "NLP Engineer", "Junior AI Engineer", "Python Developer"))
def test_unrelated_or_excluded_titles_do_not_normalize(title):
    assert normalize_raw(dict(title=title, company="Acme", url="https://example.com/jobs/1")) is None


@pytest.mark.parametrize("description", (
    "Use Python and SQL with LLM APIs.",
    "Preferred: 5+ years commercial Python experience.",
    "3-5 years commercial Python experience is not required.",
    "Must have 2 years commercial Python experience.",
))
def test_python_and_optional_experience_are_not_negative(description):
    assert not ai_negative_signals("AI Engineer", description)


@pytest.mark.parametrize("description", (
    "Must have 3-5 years commercial Python experience.",
    "Minimum 5+ years professional ML experience.",
    "At least 3 years production Python experience required.",
    "Primary focus on model training.",
    "MLOps-heavy responsibilities.",
    "Core focus is NLP research.",
))
def test_hard_requirements_and_heavy_specialisms_are_negative(description):
    assert ai_negative_signals("AI Engineer", description)


def fit(title, description):
    profile = CandidateProfile(10, frozenset({"swift", "swiftui", "uikit"}), "Senior iOS Engineer", "Kyiv", True, "B2", frozenset())
    return assess_fit(Vacancy("Acme", title, "https://example.com/job/1", "company", remote="remote", description=description), profile)


def test_ai_scoring_rewards_product_engineering_without_claiming_experience():
    plain = fit("Senior AI Engineer", "Python")
    rich = fit("Senior AI Engineer", "LLM APIs, agents, RAG, structured outputs, evals, observability, reliability, backend integration, cloud, Docker, SQL")
    required = fit("Senior AI Engineer", "Python. Must have 5+ years commercial Python experience.")
    assert rich.score > plain.score > required.score
    assert rich.recommendation == "strong"
    assert not any("is covered" in reason for reason in required.reasons)
    assert any("unverified" in reason for reason in required.reasons)
    assert fit("Senior iOS Engineer", "Swift SwiftUI UIKit").score > rich.score


def test_official_page_gate_accepts_ai():
    candidates = {}
    _add_candidate(candidates, title="Applied AI Engineer", url="/jobs/1", base_url="https://example.com", is_job_posting=True)
    assert len(candidates) == 1


def test_epam_sitemap_discovers_ai_slugs():
    urls = discover_ios_vacancy_urls("<loc>https://careers.epam.com/en/vacancy/ai-platform-engineer-1</loc>")
    assert len(urls) == 1


def test_ciklum_queries_keep_ios_and_find_ai(monkeypatch):
    queries = []
    def fetch(url):
        queries.append(url)
        title = "Senior iOS Engineer" if "keyword=ios," in url else "Applied AI Engineer"
        return {"items": [{"requisitionList": [{"Title": title, "Id": title}]}]}
    monkeypatch.setattr(bespoke, "fetch_json", fetch)
    result = bespoke.collect_ciklum()
    assert result.status == "healthy"
    assert len(queries) == 4
    assert {job["title"] for job in result.jobs} == {"Senior iOS Engineer", "Applied AI Engineer"}


@pytest.mark.parametrize("collector", (bespoke.collect_ciklum, bespoke.collect_nix_html, bespoke.collect_intellias, bespoke.collect_globallogic, bespoke.collect_sigma))
def test_secondary_failure_preserves_usable_result(monkeypatch, collector):
    import json
    calls = []
    def fetch(*args, **kwargs):
        calls.append(args)
        if len(calls) > 1:
            raise TimeoutError("secondary unavailable")
        if collector == bespoke.collect_ciklum:
            return {"items": [{"requisitionList": [{"Title": "iOS Engineer", "Id": "1"}]}]}
        if collector == bespoke.collect_sigma:
            return json.dumps({"success": True, "data": {"html": '<a class="vacancy-card-new" href="/vacancy/1"><h3 class="vacancy-card-new__title">iOS Engineer</h3></a>', "has_more": False}})
        return '<a href="https://career.intellias.com/vacancy/ios-1">iOS Engineer (#1)</a><a class="job_box" href="/ua/careers/ios-irc1"><h4>iOS Engineer</h4></a>'
    monkeypatch.setattr(bespoke, "fetch_json", fetch)
    monkeypatch.setattr(bespoke, "fetch_text", fetch)
    monkeypatch.setattr(bespoke, "fetch_text_allowing_bot_wall", fetch)
    monkeypatch.setattr(bespoke, "post_form_data", fetch)
    result = collector()
    assert result.status == "degraded"
    assert result.jobs
    assert "secondary unavailable" in result.error


@pytest.mark.parametrize("description", ("Requirements\nStrong Python expertise", "Requirements\nDevelop machine learning models", "Must have 5+ years commercial Python experience"))
def test_hard_ai_requirements_excluded(description):
    assert normalize_raw(dict(title="AI Engineer", company="Acme", url="https://example.com/1", description=description)) is None
    assert fit("AI Engineer", description).recommendation == "skip"


def test_sigma_optional_ml_is_eligible_but_required_skills_need_review():
    description = "Requirements\n1 year extensive AI SDLC experience\nHands-on MCP integrations and AI orchestration\nJavaScript/TypeScript preferred, Python also acceptable\nNICE TO HAVE\nMLOps and model training\nRAG and embeddings"
    assert normalize_raw(dict(title="AI-augmented Software Developer", company="Sigma", url="https://example.com/1", description=description))
    result = fit("Senior AI-augmented Software Developer", description)
    assert not result.blockers
    assert result.recommendation != "strong"
    assert any("Required skills need evidence" in reason for reason in result.reasons)


@pytest.mark.parametrize("requirements, accepted", (("<h2>Requirements</h2><p>Strong Python expertise</p>", False), ("<h2>Requirements</h2><p>Hands-on MCP integrations</p><h2>Nice to have</h2><p>Strong Python expertise</p>", True)))
def test_sigma_detail_requirements_control_emission(monkeypatch, requirements, accepted):
    import json
    monkeypatch.setattr(bespoke, "post_form_data", lambda *args, **kwargs: json.dumps({"success": True, "data": {"html": '<a class="vacancy-card-new" href="/vacancy/ai-augmented-software-developer/"><h3 class="vacancy-card-new__title">AI-augmented Software Developer</h3></a>', "has_more": False}}))
    monkeypatch.setattr(bespoke, "fetch_text", lambda *args, **kwargs: '<main>' + requirements + '</main>')
    result = bespoke.collect_sigma()
    assert result.status == "healthy"
    assert bool(result.jobs) == accepted
    if accepted:
        assert "MCP" in result.jobs[0]["description"]


def test_inline_html_keeps_python_requirement_together():
    description = "<li>Strong knowledge of <strong>Python</strong> is required.</li>"
    assert normalize_raw(dict(title="AI Engineer", company="Acme", url="https://example.com/1", description=description)) is None


def test_strong_typescript_does_not_imply_strong_python():
    description = "Strong TypeScript development skills and basic familiarity with Python."
    assert normalize_raw(dict(title="AI Engineer", company="Acme", url="https://example.com/1", description=description))


@pytest.mark.parametrize("collector", (bespoke.collect_infopulse, bespoke.collect_luxoft, bespoke.collect_dataart))
def test_remaining_scoped_sources_collect_ai(monkeypatch, collector):
    calls = []
    def fetch(url, **kwargs):
        calls.append(url)
        if collector == bespoke.collect_dataart:
            title = "iOS Engineer" if "?" in url else "AI Software Engineer"
            return {"items": [{"title": title, "slug": title}]}
        if collector == bespoke.collect_infopulse:
            title = "iOS Engineer" if "q=iOS" in url else "AI Software Engineer"
            return f'<a href="/job/{len(calls)}">{title}</a>'
        title = "iOS Engineer" if "?" in url else "AI Software Engineer"
        return f'<a href="/jobs/role-{len(calls)}"><h2>{title}</h2></a>'
    monkeypatch.setattr(bespoke, "fetch_json", fetch)
    monkeypatch.setattr(bespoke, "fetch_text", fetch)
    monkeypatch.setattr(bespoke, "_luxoft_detail_location", lambda *args, **kwargs: None, raising=False)
    result = collector()
    assert result.is_usable
    assert any(job["title"] == "AI Software Engineer" for job in result.jobs)
    assert any(job["title"] == "iOS Engineer" for job in result.jobs)
