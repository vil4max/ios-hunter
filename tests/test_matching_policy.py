from types import SimpleNamespace

import pytest

from analytics.fit_score import CandidateProfile, assess_fit
from parser.normalize import Vacancy, ai_requirement_blockers, is_inbox_candidate, is_location_eligible, normalize_raw
from project_sync.sync import build_issue_body
from scripts.score_inbox import _fallback_vacancy

PROFILE = CandidateProfile(13, frozenset({'swift', 'uikit'}), 'Senior iOS Engineer', 'Kyiv', True, 'B2', frozenset())


@pytest.mark.parametrize('location,remote,eligible', [
    ('US only, remote', 'remote', False),
    ('Remote (Poland only)', 'remote', False),
    ('Ukraine', 'onsite', False),
    ('Ukraine', 'unknown', False),
    ('Lviv', 'hybrid', False),
    ('Lviv', 'remote', True),
    ('Eastern Europe', 'remote', False),
    ('Kyiv', 'onsite', True),
    ('віддалено', 'unknown', True),
    ('Worldwide remote', 'remote', True),
    ('Work from home', 'unknown', True),
    (None, 'unknown', True),
])
def test_inbox_and_scoring_share_geo(location, remote, eligible):
    vacancy = Vacancy('Acme', 'Senior iOS Engineer', 'https://example.com/job', 'company', location, remote)
    assert is_location_eligible(location, remote) is eligible
    assert is_inbox_candidate(vacancy) is eligible
    assert ('location mismatch' not in assess_fit(vacancy, PROFILE).blockers) is eligible


@pytest.mark.parametrize('title,description,eligible', [
    ('macOS C++ Developer', 'Develop AppKit desktop applications', False),
    ('Senior iOS Engineer', None, True),
    ('AI Architect', None, False),
    ('Senior AI Engineer', 'Apply now for Senior AI Engineer', False),
    ('AI Software Engineer', 'Develop integrations using LLM APIs, agents and RAG with TypeScript. Python is optional.', True),
])
def test_primary_track_and_ai_evidence(title, description, eligible):
    vacancy = Vacancy('Acme', title, 'https://example.com/job', 'company', remote='remote', description=description)
    assert is_inbox_candidate(vacancy) is eligible


@pytest.mark.parametrize('description,blocked', [
    ('Requirements\n5+ years of commercial Python experience', True),
    ('Requirements\nStrong Python required, TypeScript preferred', True),
    ('Requirements\nStrong Python required and TypeScript preferred', True),
    ('Requirements\nMCP integrations\nNice to have\n5+ years of commercial Python experience', False),
    ('Requirements\n3-5 years commercial Python experience is not required.', False),
    ('Use RAG and embeddings; Python is optional.', False),
    ('Requirements\nStrong TypeScript, Python also acceptable', False),
])
def test_required_and_optional_clauses(description, blocked):
    assert bool(ai_requirement_blockers('AI Engineer', description)) is blocked


def test_unknown_location_warning_roundtrip():
    original = Vacancy('Acme', 'Senior iOS Engineer', 'https://example.com/job', 'company')
    card = SimpleNamespace(company=original.company, title=original.title, url=original.url,
                           canonical_url=original.canonical_url, source=original.source,
                           body=build_issue_body(original))
    restored = _fallback_vacancy(card)
    assert restored.location is None
    assert 'location mismatch' not in assess_fit(restored, PROFILE).blockers


@pytest.mark.parametrize('description,location,mode,eligible', [
    ('This role is not remote.', 'Ukraine', 'onsite', False),
    ('Remote work is not available.', 'Ukraine', 'onsite', False),
    ('Hybrid role with remote days.', 'Lviv', 'hybrid', False),
    ('On-site work with remote collaboration.', 'Lviv', 'onsite', False),
    ('This role is not remote.', 'Kyiv', 'onsite', True),
    ('Fully remote; office visits are optional.', 'Ukraine', 'remote', True),
])
def test_normalized_work_mode_respects_office_constraints(description, location, mode, eligible):
    vacancy = normalize_raw(dict(company='Acme', title='Senior iOS Engineer',
                                 url='https://example.com/job', location=location,
                                 description=description, remote='unknown'))
    assert vacancy.remote == mode
    assert is_inbox_candidate(vacancy) is eligible
