from __future__ import annotations

import json
import os
import re
import time
from typing import Protocol, TypeVar

import requests
from pydantic import BaseModel, ValidationError

from integrations.http_client import post_json

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    def enabled(self) -> bool: ...

    def generate_structured(
        self,
        system: str,
        user: str,
        schema: type[T],
    ) -> tuple[T, int | None, int | None]: ...


class NoOpProvider:
    @property
    def provider_name(self) -> str:
        return "noop"

    @property
    def model_name(self) -> str:
        return "none"

    def enabled(self) -> bool:
        return False

    def generate_structured(
        self,
        system: str,
        user: str,
        schema: type[T],
    ) -> tuple[T, int | None, int | None]:
        _ = (system, user, schema)
        raise RuntimeError("NoOpProvider cannot generate structured output")


def _extract_json(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response")
    return json.loads(stripped[start : end + 1])


def _parse_structured(text: str, schema: type[T]) -> T:
    return schema.model_validate(_extract_json(text))


class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self.model

    def enabled(self) -> bool:
        return bool(self.api_key)

    def generate_structured(
        self,
        system: str,
        user: str,
        schema: type[T],
    ) -> tuple[T, int | None, int | None]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": True,
                },
            },
        }
        data = self._post_with_retry(payload)
        text = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {})
        return (
            _parse_structured(text, schema),
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
        )

    def _post_with_retry(self, payload: dict) -> dict:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return post_json(
                    "https://api.openai.com/v1/chat/completions",
                    payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=60,
                )
            except Exception as error:  # noqa: BLE001
                last_error = error
                if attempt < 2:
                    delay = 2**attempt
                    if isinstance(error, requests.HTTPError) and error.response is not None:
                        if error.response.status_code == 429:
                            delay = 15 * (attempt + 1)
                    time.sleep(delay)
        raise last_error or RuntimeError("OpenAI request failed")


class GeminiProvider:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key
        self.model = model

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self.model

    def enabled(self) -> bool:
        return bool(self.api_key)

    def generate_structured(
        self,
        system: str,
        user: str,
        schema: type[T],
    ) -> tuple[T, int | None, int | None]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "responseSchema": schema.model_json_schema(),
            },
        }
        data = self._post_with_retry(url, payload)
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        usage = data.get("usageMetadata", {})
        return (
            _parse_structured(text, schema),
            usage.get("promptTokenCount"),
            usage.get("candidatesTokenCount"),
        )

    def _post_with_retry(self, url: str, payload: dict) -> dict:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return post_json(
                    url,
                    payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": self.api_key,
                    },
                    timeout=60,
                )
            except Exception as error:  # noqa: BLE001
                last_error = error
                if attempt < 2:
                    delay = 2**attempt
                    if isinstance(error, requests.HTTPError) and error.response is not None:
                        if error.response.status_code == 429:
                            delay = 15 * (attempt + 1)
                    time.sleep(delay)
        raise last_error or RuntimeError("Gemini request failed")


def create_llm_provider() -> LLMProvider:
    provider = os.environ.get("AI_PROVIDER", "").strip().lower()
    model = os.environ.get("AI_MODEL", "").strip()

    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if provider == "openai" and openai_key:
        return OpenAIProvider(openai_key, model or "gpt-4o-mini")
    if provider == "gemini" and gemini_key:
        return GeminiProvider(gemini_key, model or "gemini-2.0-flash")

    if openai_key and provider != "gemini":
        return OpenAIProvider(openai_key, model or "gpt-4o-mini")
    if gemini_key:
        return GeminiProvider(gemini_key, model or "gemini-2.0-flash")

    return NoOpProvider()


def format_validation_errors(error: ValidationError) -> str:
    return "; ".join(f"{item['loc']}: {item['msg']}" for item in error.errors())
