import json
from types import SimpleNamespace

import pytest

from collector import bespoke, company_watchlist as watchlist, generic
from parser.normalize import is_inbox_candidate, normalize_raw


DESCRIPTION = 'Build reliable LLM APIs and agent orchestration with structured outputs and evaluations.'
BASE = 'https://acme.test/careers'


def test_nested_jsonld_enriches_existing_anchor_and_location():
    payload = {'@graph': [{'@type': ['Thing', 'JobPosting'], 'title': 'AI Engineer',
                         'url': '/jobs/ai', 'description': DESCRIPTION,
                         'jobLocationType': 'TELECOMMUTE',
                         'applicantLocationRequirements': {'@type': 'Country', 'name': 'US'}}]}
    html = '<a href="/jobs/ai">AI Engineer</a>'
    html += f'<script type="application/ld+json">{json.dumps(payload)}</script>'
    jobs, _ = watchlist.extract_ios_jobs('Acme', BASE, html)
    assert len(jobs) == 1
    assert jobs[0]['description'] == DESCRIPTION
    assert jobs[0]['location'] == 'US / Remote'
    assert not is_inbox_candidate(normalize_raw(jobs[0]))


@pytest.mark.parametrize('adapter', ['conscensia', 'wordpress'])
def test_wordpress_retains_rendered_requirements(monkeypatch, adapter):
    payload = [{'id': 1, 'title': {'rendered': 'AI Engineer'},
                'content': {'rendered': DESCRIPTION}, 'link': 'https://acme.test/jobs/ai'}]
    if adapter == 'conscensia':
        monkeypatch.setattr(watchlist, 'fetch_json', lambda _: payload)
        jobs, _ = watchlist._collect_conscensia('Acme')
    else:
        monkeypatch.setattr(generic, 'fetch_json', lambda _: payload)
        jobs = generic.collect_wp_rest('Acme', BASE).jobs
    assert jobs[0]['description'] == DESCRIPTION
    assert is_inbox_candidate(normalize_raw(jobs[0]))


def collect(monkeypatch, detail):
    listing = '<a href="/jobs/ios">Senior iOS Engineer</a><a href="/jobs/ai">AI Engineer</a>'
    monkeypatch.setattr(watchlist, 'fetch_text', lambda _: listing)
    monkeypatch.setattr(watchlist, '_fetch_ai_detail', detail)
    return watchlist.collect_watchlist_company({'name': 'Acme', 'career_url': BASE})


def test_matching_detail_is_hydrated_but_other_roles_are_removed(monkeypatch):
    html = f'<main><h1>AI Engineer</h1><p>{DESCRIPTION}</p>'
    html += '<aside><h2>Python Engineer</h2>Strong Python required</aside></main>'
    result = collect(monkeypatch, lambda *_: html)
    assert result.status == 'healthy'
    assert len(result.jobs) == 2
    ai = next(job for job in result.jobs if job['title'] == 'AI Engineer')
    assert 'Python' not in ai['description']
    assert is_inbox_candidate(normalize_raw(ai))


@pytest.mark.parametrize('html', [
    f'<main><h1>Different Engineer</h1><p>{DESCRIPTION}</p></main>',
    f'<main><h1>AI Engineer</h1><h1>Other Engineer</h1><p>{DESCRIPTION}</p></main>',
    f'<nav>{DESCRIPTION}</nav>',
])
def test_unverified_detail_is_degraded_and_preserves_ios(monkeypatch, html):
    result = collect(monkeypatch, lambda *_: html)
    assert result.status == 'degraded'
    assert result.jobs[0]['title'] == 'Senior iOS Engineer'
    assert not is_inbox_candidate(normalize_raw(result.jobs[1]))


def test_failed_detail_does_not_destroy_ios(monkeypatch):
    def failed(*_):
        raise RuntimeError('403')
    result = collect(monkeypatch, failed)
    assert result.status == 'degraded'
    assert '403' in result.error
    assert result.jobs[0]['title'] == 'Senior iOS Engineer'


def test_detail_budget_leaves_deferred_candidates_ineligible(monkeypatch):
    jobs = [{'title': 'AI Engineer', 'url': f'https://acme.test/jobs/{i}'} for i in range(10)]
    calls = []
    monkeypatch.setattr(watchlist, '_fetch_ai_detail',
                        lambda url, _: calls.append(url) or f'<main><h1>AI Engineer</h1>{DESCRIPTION}</main>')
    errors = watchlist._hydrate_ai_details(jobs, BASE)
    assert len(calls) == 8
    assert errors == ['AI detail limit: 2 deferred']
    assert 'description' not in jobs[-1]


@pytest.mark.parametrize('url', ['https://other.test/jobs/ai', 'https://user@acme.test/jobs/ai',
                                 'http://acme.test/jobs/ai', 'https://127.0.0.1/jobs/ai'])
def test_detail_rejects_unsafe_origin_without_request(monkeypatch, url):
    monkeypatch.setattr(watchlist.requests, 'get', lambda *_a, **_k: pytest.fail('unexpected request'))
    with pytest.raises(ValueError):
        watchlist._fetch_ai_detail(url, BASE)


def test_detail_does_not_follow_cross_origin_redirect(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        assert kwargs['allow_redirects'] is False
        return SimpleNamespace(status_code=302, headers={'Location': 'http://127.0.0.1/private'})
    monkeypatch.setattr(watchlist.requests, 'get', get)
    with pytest.raises(ValueError):
        watchlist._fetch_ai_detail('https://acme.test/jobs/ai', BASE)
    assert calls == ['https://acme.test/jobs/ai']


def test_rbi_keeps_verified_sitemap_job_when_listing_fails(monkeypatch):
    def fetch(url):
        if url.endswith('sitemap.xml'):
            return '<loc>https://www.rbi-ri.com.ua/career/ai-engineer</loc>'
        if url.endswith('/career'):
            raise RuntimeError('listing 403')
        return f'<main><h1>AI Engineer</h1>{DESCRIPTION}</main>'
    monkeypatch.setattr(bespoke, 'fetch_text', fetch)
    result = bespoke.collect_rbi()
    assert result.status == 'degraded'
    assert 'listing 403' in result.error
    assert len(result.jobs) == 1
    assert is_inbox_candidate(normalize_raw(result.jobs[0]))


def test_rbi_all_failed_detail_pages_are_not_healthy(monkeypatch):
    monkeypatch.setattr(bespoke, 'fetch_text', lambda url:
                        '<loc>https://www.rbi-ri.com.ua/career/ai-engineer</loc>'
                        if url.endswith('sitemap.xml') else '<html>No verified job</html>')
    result = bespoke.collect_rbi()
    assert result.status == 'failed'
    assert result.jobs == []


def test_hydrated_mandatory_python_requirements_still_block_inbox(monkeypatch):
    html = f'<main><h1>AI Engineer</h1><p>{DESCRIPTION}</p>'
    html += '<h2>Requirements</h2><p>5+ years of commercial Python experience required</p></main>'
    result = collect(monkeypatch, lambda *_: html)
    assert result.status == 'healthy'
    ai = next(job for job in result.jobs if job['title'] == 'AI Engineer')
    assert 'Python' in ai['description']
    assert normalize_raw(ai) is None


def test_rbi_generic_career_page_does_not_verify_sitemap_job(monkeypatch):
    monkeypatch.setattr(bespoke, 'fetch_text', lambda url:
                        '<loc>https://www.rbi-ri.com.ua/career/ios-engineer</loc>'
                        if url.endswith('sitemap.xml') else '<title>Careers</title>')
    result = bespoke.collect_rbi()
    assert result.status == 'failed'
    assert result.jobs == []
