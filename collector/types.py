from __future__ import annotations

from dataclasses import dataclass
from typing import Any


STATUS_HEALTHY = "healthy"
STATUS_DEGRADED = "degraded"
STATUS_FAILED = "failed"


@dataclass
class SourceResult:
    source_id: str
    source_name: str
    source_url: str | None
    jobs: list[dict[str, Any]]
    status: str
    error: str | None
    response_ms: int
    items_scanned: int = 0
    empty_is_healthy: bool = False

    @property
    def is_usable(self) -> bool:
        return self.status != STATUS_FAILED


@dataclass
class CollectResult:
    source_results: list[SourceResult]
