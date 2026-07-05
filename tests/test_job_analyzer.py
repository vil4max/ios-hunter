from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from ai.job_analyzer import JobAnalyzer, validate_analysis_output
from ai.models import JobAnalysisOutput
from ai.providers import LLMProvider
from apply.matcher import MatchResult
from tests.conftest import make_job_record, make_vacancy


class FakeProvider(LLMProvider):
    def __init__(self, outputs: list[JobAnalysisOutput]) -> None:
        self._outputs = outputs
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"

    def enabled(self) -> bool:
        return True

    def generate_structured(self, system: str, user: str, schema: type) -> tuple[Any, int | None, int | None]:
        _ = (system, user, schema)
        if self.calls >= len(self._outputs):
            raise RuntimeError("no more outputs")
        output = self._outputs[self.calls]
        self.calls += 1
        return output, 100, 50


def _analysis_output(**overrides) -> JobAnalysisOutput:
    defaults = {
        "fit_score": 82,
        "apply_priority": "high",
        "confidence": "high",
        "seniority_match": "strong",
        "role_type": "platform",
        "domain_match": "strong",
        "architecture_match": "medium",
        "employment_type": "remote",
        "location_compatibility": "compatible",
        "language_risk": "none",
        "strong_matches": ["SDK cross-app integration"],
        "must_have_gaps": [],
        "nice_to_have_gaps": ["TCA"],
        "risk_factors": [],
        "recommended_resume": "sdk",
        "referenced_fact_ids": ["pasha_premium_sdk"],
        "reason": "Strong SDK platform fit.",
    }
    defaults.update(overrides)
    return JobAnalysisOutput.model_validate(defaults)


def test_validate_analysis_rejects_unknown_fact_ids() -> None:
    output = _analysis_output(referenced_fact_ids=["unknown_fact"])

    errors = validate_analysis_output(output, {"pasha_premium_sdk"})

    assert errors
    assert "unknown referenced_fact_ids" in errors[0]


def test_job_analyzer_uses_cache(repo, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "prompts").mkdir()
    (tmp_path / "config/profile.yaml").write_text("name: Test\nskills: []\nenglish:\n  level: B1\n", encoding="utf-8")
    (tmp_path / "config/career_facts.yaml").write_text(
        "facts:\n  - id: pasha_premium_sdk\n    facts: [Shared SDK]\n", encoding="utf-8"
    )
    (tmp_path / "config/skills.yaml").write_text("SDK:\n  - sdk\n", encoding="utf-8")
    (tmp_path / "prompts/job_analysis.md").write_text(
        "Profile\n{profile_summary}\nFacts\n{career_facts}\n"
        "Prefilter {prefilter_score} strong {strong_skills} missing {missing_skills} remote {remote_ok}\n"
        "Job {company} {title} {location} {remote}\n{description}\n",
        encoding="utf-8",
    )

    job = make_job_record(make_vacancy())
    repo.upsert_job(job)
    match = MatchResult(score=70, strong=["SDK"], missing=[], remote_ok=True, resume_version="sdk")
    provider = FakeProvider([_analysis_output()])

    analyzer = JobAnalyzer(provider=provider, base_dir=tmp_path)
    first = analyzer.analyze_job(repo, job, match)
    second = analyzer.analyze_job(repo, job, match)

    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert provider.calls == 1


def test_job_analysis_output_schema_validation() -> None:
    with pytest.raises(ValidationError):
        JobAnalysisOutput.model_validate({"fit_score": 200})
