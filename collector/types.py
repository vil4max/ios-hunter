from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SourceResult:
    source_id: str
    source_name: str
    source_url: str | None
    jobs: list[dict[str, Any]]
    status: str
    error: str | None
    response_ms: int


@dataclass
class SwiftCollectorMeta:
    sources_total: int
    sources_failed: int
    failed_companies: list[str]

    @property
    def sources_ok(self) -> int:
        return self.sources_total - self.sources_failed


@dataclass
class CollectResult:
    source_results: list[SourceResult]
    swift_meta: SwiftCollectorMeta | None
