import json

from integrations import detail_cache
from integrations.detail_cache import DetailCache
from collector import company_watchlist


DESCRIPTION = 'Build reliable LLM APIs with tool orchestration and structured outputs for production services.'
URL = 'https://acme.test/jobs/ai'


def test_cache_is_opt_in(monkeypatch):
    monkeypatch.delenv('DETAIL_CACHE_PATH', raising=False)
    cache = DetailCache.from_environment()
    cache.put(URL, 'AI Engineer', DESCRIPTION, None)
    assert cache.path is None
    assert cache.get(URL, 'AI Engineer') is None


def test_persistent_cache_expires_and_title_change_misses(tmp_path, monkeypatch):
    path = tmp_path / 'cache.json'
    monkeypatch.setattr(detail_cache.time, 'time', lambda: 1000)
    DetailCache(path).put(URL, 'AI Engineer', DESCRIPTION, 'Ukraine / Remote')
    assert DetailCache(path).get(URL, 'AI Engineer') == (DESCRIPTION, 'Ukraine / Remote')
    assert DetailCache(path).get(URL, 'Python Engineer') is None
    monkeypatch.setattr(detail_cache.time, 'time', lambda: 1000 + detail_cache.TTL_SECONDS)
    assert DetailCache(path).get(URL, 'AI Engineer') is None


def test_corrupt_cache_is_a_cold_start(tmp_path):
    path = tmp_path / 'cache.json'
    for contents in ('not json', '[]', '{"version":1,"entries":{"key":null}}'):
        path.write_text(contents)
        assert DetailCache(path).get(URL, 'AI Engineer') is None
    DetailCache(path).put(URL, 'AI Engineer', DESCRIPTION, None)
    assert DetailCache(path).get(URL, 'AI Engineer') == (DESCRIPTION, None)
    assert list(tmp_path.glob('.detail-cache-*')) == []


def test_cache_evicts_oldest_at_capacity(tmp_path, monkeypatch):
    monkeypatch.setattr(detail_cache, 'MAX_ENTRIES', 2)
    path = tmp_path / 'cache.json'
    for i in range(3):
        monkeypatch.setattr(detail_cache.time, 'time', lambda i=i: 1000+i)
        DetailCache(path).put(URL + str(i), 'AI Engineer', DESCRIPTION, None)
    assert DetailCache(path).get(URL+'0', 'AI Engineer') is None
    assert DetailCache(path).get(URL+'2', 'AI Engineer') is not None
    assert len(json.loads(path.read_text())['entries']) == 2


def test_failed_atomic_replace_preserves_previous_file(tmp_path, monkeypatch):
    path = tmp_path / 'cache.json'
    cache = DetailCache(path)
    cache.put(URL, 'AI Engineer', DESCRIPTION, None)
    previous = path.read_text()
    monkeypatch.setattr(detail_cache.os, 'replace', lambda *_: (_ for _ in ()).throw(OSError('disk full')))
    cache.put(URL, 'AI Engineer', 'replacement', None)
    assert path.read_text() == previous
    assert list(tmp_path.glob('.detail-cache-*')) == []


def test_hydration_caches_only_verified_success_and_never_serves_stale(tmp_path, monkeypatch):
    monkeypatch.setenv('DETAIL_CACHE_PATH', str(tmp_path / 'cache.json'))
    monkeypatch.setattr(detail_cache.time, 'time', lambda: 1000)
    calls = []
    def fetch(*_):
        calls.append(1)
        return f'<main><h1>AI Engineer</h1>{DESCRIPTION}</main>'
    monkeypatch.setattr(company_watchlist, '_fetch_ai_detail', fetch)
    def jobs():
        return [{'title': 'AI Engineer', 'url': URL}]
    first, second = jobs(), jobs()
    assert company_watchlist._hydrate_ai_details(first, 'https://acme.test/careers') == []
    assert company_watchlist._hydrate_ai_details(second, 'https://acme.test/careers') == []
    assert len(calls) == 1
    monkeypatch.setattr(detail_cache.time, 'time', lambda: 1000+detail_cache.TTL_SECONDS)
    monkeypatch.setattr(company_watchlist, '_fetch_ai_detail', lambda *_: (_ for _ in ()).throw(RuntimeError('503')))
    stale = jobs()
    assert company_watchlist._hydrate_ai_details(stale, 'https://acme.test/careers')
    assert 'description' not in stale[0]


def test_failed_requirements_are_not_cached(tmp_path, monkeypatch):
    path = tmp_path / 'cache.json'
    monkeypatch.setenv('DETAIL_CACHE_PATH', str(path))
    monkeypatch.setattr(company_watchlist, '_fetch_ai_detail', lambda *_: '<main><h1>AI Engineer</h1></main>')
    jobs = [{'title': 'AI Engineer', 'url': URL}]
    assert company_watchlist._hydrate_ai_details(jobs, 'https://acme.test/careers')
    assert not path.exists()
