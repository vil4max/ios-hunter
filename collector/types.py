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
