from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from ai.fingerprints import candidate_profile_hash, job_content_hash
from ai.models import PROMPT_VERSION, JobAnalysisOutput, JobAnalysisRecord
from ai.providers import LLMProvider, NoOpProvider, create_llm_provider
from apply.matcher import MatchResult, load_profile
from database.repository import JobRecord, JobRepository, utc_now
from integrations.template_render import render_named_template


def load_career_facts(config_path: str | Path = "config/career_facts.yaml") -> dict:
    path = Path(config_path)
    if not path.exists():
        return {"facts": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"facts": []}


def valid_fact_ids(career_facts: dict) -> set[str]:
    return {str(item["id"]) for item in career_facts.get("facts", []) if item.get("id")}


def build_profile_summary(profile: dict) -> str:
    lines = [
        f"name: {profile.get('name', '')}",
        f"headline: {profile.get('headline', '')}",
        f"experience_years: {profile.get('experience_years', '')}",
        f"remote_preference: {profile.get('remote_preference', '')}",
        f"english.level: {profile.get('english', {}).get('level', '')}",
        f"skills: {', '.join(profile.get('skills', []))}",
    ]
    return "\n".join(lines)


def build_analysis_prompt(
    job: JobRecord,
    match: MatchResult,
    profile: dict,
    career_facts: dict,
    template_path: Path,
) -> str:
    template = template_path.read_text(encoding="utf-8")
    return render_named_template(
        template,
        {
            "profile_summary": build_profile_summary(profile),
            "career_facts": yaml.safe_dump(career_facts, sort_keys=False).strip(),
            "prefilter_score": str(match.score),
            "strong_skills": ", ".join(match.strong) or "—",
            "missing_skills": ", ".join(match.missing) or "—",
            "remote_ok": str(match.remote_ok),
            "company": job.company,
            "title": job.title,
            "location": job.location or "unknown",
            "remote": job.remote or "unknown",
            "description": (job.description or job.title)[:6000],
        },
    )


def validate_analysis_output(output: JobAnalysisOutput, fact_ids: set[str]) -> list[str]:
    errors: list[str] = []
    invalid_ids = [fact_id for fact_id in output.referenced_fact_ids if fact_id not in fact_ids]
    if invalid_ids:
        errors.append(f"unknown referenced_fact_ids: {', '.join(invalid_ids)}")
    if output.strong_matches and not output.referenced_fact_ids:
        errors.append("strong_matches require referenced_fact_ids")
    if output.fit_score > 85 and not output.referenced_fact_ids:
        errors.append("high fit_score requires referenced_fact_ids")
    if output.recommended_resume not in {"ai", "sdk", "product"}:
        errors.append("invalid recommended_resume")
    return errors


def downgrade_output(output: JobAnalysisOutput, reason: str) -> JobAnalysisOutput:
    data = output.model_dump()
    data["apply_priority"] = "skip"
    data["fit_score"] = min(output.fit_score, 40)
    data["confidence"] = "low"
    data["reason"] = reason[:280]
    return JobAnalysisOutput.model_validate(data)


class JobAnalyzer:
    def __init__(
        self,
        provider: LLMProvider | None = None,
        base_dir: Path | None = None,
        prompt_path: Path | None = None,
    ) -> None:
        self.base_dir = base_dir or Path.cwd()
        self.provider = provider or create_llm_provider()
        self.prompt_path = prompt_path or (self.base_dir / "prompts/job_analysis.md")

    def enabled(self) -> bool:
        return self.provider.enabled()

    def analyze_job(
        self,
        repo: JobRepository,
        job: JobRecord,
        match: MatchResult,
        profile: dict | None = None,
    ) -> JobAnalysisRecord | None:
        if not self.enabled():
            return None

        profile = profile or load_profile(self.base_dir / "config/profile.yaml")
        career_facts = load_career_facts(self.base_dir / "config/career_facts.yaml")
        content_hash = job_content_hash(job)
        profile_hash = candidate_profile_hash(self.base_dir)
        model = self.provider.model_name

        cached = repo.get_cached_job_analysis(
            job_id=job.id,
            job_content_hash=content_hash,
            candidate_profile_hash=profile_hash,
            prompt_version=PROMPT_VERSION,
            model=model,
        )
        if cached is not None:
            return cached

        fact_ids = valid_fact_ids(career_facts)
        user_prompt = build_analysis_prompt(job, match, profile, career_facts, self.prompt_path)
        system_prompt = (
            "You are a job intelligence analyzer for a senior iOS engineer. "
            "Respond with JSON only."
        )

        output, input_tokens, output_tokens = self._generate_with_validation(
            system_prompt,
            user_prompt,
            fact_ids,
        )

        record = JobAnalysisRecord(
            job_id=job.id,
            output=output,
            prefilter_score=match.score,
            job_content_hash=content_hash,
            candidate_profile_hash=profile_hash,
            prompt_version=PROMPT_VERSION,
            provider=self.provider.provider_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            analyzed_at=utc_now(),
        )
        return repo.save_job_analysis(record)

    def _generate_with_validation(
        self,
        system_prompt: str,
        user_prompt: str,
        fact_ids: set[str],
    ) -> tuple[JobAnalysisOutput, int | None, int | None]:
        if isinstance(self.provider, NoOpProvider):
            raise RuntimeError("NoOpProvider cannot analyze jobs")

        try:
            output, input_tokens, output_tokens = self.provider.generate_structured(
                system_prompt,
                user_prompt,
                JobAnalysisOutput,
            )
        except (ValidationError, ValueError) as error:
            retry_prompt = (
                f"{user_prompt}\n\nPrevious response was invalid: {error}. "
                "Return valid JSON matching the schema."
            )
            output, input_tokens, output_tokens = self.provider.generate_structured(
                system_prompt,
                retry_prompt,
                JobAnalysisOutput,
            )

        errors = validate_analysis_output(output, fact_ids)
        if errors:
            output = downgrade_output(output, errors[0])
        return output, input_tokens, output_tokens
