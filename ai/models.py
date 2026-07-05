from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ApplyPriority = Literal["skip", "low", "medium", "high"]
Confidence = Literal["low", "medium", "high"]
SeniorityMatch = Literal["weak", "medium", "strong"]
MatchLevel = Literal["weak", "medium", "strong"]
EmploymentType = Literal["remote", "hybrid", "onsite", "unclear"]
LocationCompatibility = Literal["compatible", "unclear", "incompatible"]
LanguageRisk = Literal["none", "possible", "blocker"]
ResumeVariant = Literal["ai", "sdk", "product"]

PROMPT_VERSION = "job_analysis_v1"


class JobAnalysisOutput(BaseModel):
    fit_score: int = Field(ge=0, le=100)
    apply_priority: ApplyPriority
    confidence: Confidence
    seniority_match: SeniorityMatch
    role_type: str = Field(max_length=64)
    domain_match: MatchLevel
    architecture_match: MatchLevel
    employment_type: EmploymentType
    location_compatibility: LocationCompatibility
    language_risk: LanguageRisk
    strong_matches: list[str] = Field(default_factory=list, max_length=5)
    must_have_gaps: list[str] = Field(default_factory=list, max_length=5)
    nice_to_have_gaps: list[str] = Field(default_factory=list, max_length=5)
    risk_factors: list[str] = Field(default_factory=list, max_length=5)
    recommended_resume: ResumeVariant
    referenced_fact_ids: list[str] = Field(default_factory=list, max_length=8)
    reason: str = Field(max_length=280)


class JobAnalysisRecord(BaseModel):
    id: Optional[int] = None
    job_id: str
    output: JobAnalysisOutput
    prefilter_score: int
    job_content_hash: str
    candidate_profile_hash: str
    prompt_version: str
    provider: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    analyzed_at: str
