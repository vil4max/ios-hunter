from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol


@dataclass
class AnalysisResult:
    summary: str
    match_score: int | None = None
    cover_letter: str | None = None


class AIAnalyzer(Protocol):
    def enabled(self) -> bool: ...

    def summarize_week(self, context: str) -> AnalysisResult: ...

    def match_job(self, resume: str, job_description: str) -> AnalysisResult: ...

    def cover_letter(self, resume: str, job_title: str, company: str, description: str) -> AnalysisResult: ...


class NoOpAnalyzer:
    def enabled(self) -> bool:
        return False

    def summarize_week(self, context: str) -> AnalysisResult:
        return AnalysisResult(summary="")

    def match_job(self, resume: str, job_description: str) -> AnalysisResult:
        return AnalysisResult(summary="", match_score=None)

    def cover_letter(self, resume: str, job_title: str, company: str, description: str) -> AnalysisResult:
        return AnalysisResult(summary="", cover_letter=None)


class OpenAIAnalyzer:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    def enabled(self) -> bool:
        return bool(self.api_key)

    def summarize_week(self, context: str) -> AnalysisResult:
        prompt = f"Summarize this week's iOS job market activity in 2-3 sentences:\n\n{context}"
        return AnalysisResult(summary=self._complete(prompt))

    def match_job(self, resume: str, job_description: str) -> AnalysisResult:
        prompt = (
            "Rate this resume against the job description from 0-100. "
            "Reply with only the number on the first line, then a one-sentence rationale.\n\n"
            f"Resume:\n{resume}\n\nJob:\n{job_description}"
        )
        text = self._complete(prompt)
        score = None
        lines = text.strip().splitlines()
        if lines:
            try:
                score = int(lines[0].strip().rstrip("%"))
            except ValueError:
                score = None
        return AnalysisResult(summary=text, match_score=score)

    def cover_letter(self, resume: str, job_title: str, company: str, description: str) -> AnalysisResult:
        prompt = (
            f"Write a concise cover letter for {job_title} at {company}. "
            f"Use the resume and job description below.\n\n"
            f"Resume:\n{resume}\n\nJob:\n{description}"
        )
        letter = self._complete(prompt)
        return AnalysisResult(summary=letter, cover_letter=letter)

    def _complete(self, prompt: str) -> str:
        import json
        import urllib.request

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()


class GeminiAnalyzer:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key
        self.model = model

    def enabled(self) -> bool:
        return bool(self.api_key)

    def summarize_week(self, context: str) -> AnalysisResult:
        prompt = f"Summarize this week's iOS job market activity in 2-3 sentences:\n\n{context}"
        return AnalysisResult(summary=self._complete(prompt))

    def match_job(self, resume: str, job_description: str) -> AnalysisResult:
        prompt = (
            "Rate this resume against the job description from 0-100. "
            "Reply with only the number on the first line, then a one-sentence rationale.\n\n"
            f"Resume:\n{resume}\n\nJob:\n{job_description}"
        )
        text = self._complete(prompt)
        score = None
        lines = text.strip().splitlines()
        if lines:
            try:
                score = int(lines[0].strip().rstrip("%"))
            except ValueError:
                score = None
        return AnalysisResult(summary=text, match_score=score)

    def cover_letter(self, resume: str, job_title: str, company: str, description: str) -> AnalysisResult:
        prompt = (
            f"Write a concise cover letter for {job_title} at {company}. "
            f"Use the resume and job description below.\n\n"
            f"Resume:\n{resume}\n\nJob:\n{description}"
        )
        letter = self._complete(prompt)
        return AnalysisResult(summary=letter, cover_letter=letter)

    def _complete(self, prompt: str) -> str:
        import json
        import urllib.request

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def create_analyzer() -> AIAnalyzer:
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key:
        return OpenAIAnalyzer(openai_key)

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        return GeminiAnalyzer(gemini_key)

    return NoOpAnalyzer()
