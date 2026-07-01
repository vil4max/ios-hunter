from __future__ import annotations

from collector.types import SourceResult


def render_health_report(results: list[SourceResult], runtime_seconds: float, duplicates_removed: int) -> str:
    total = len(results)
    failed = [result for result in results if result.status == "failed"]
    healthy_count = total - len(failed)

    lines = [
        "Collector Health",
        "",
        f"Sources:      {total}",
        f"Healthy:      {healthy_count}",
        f"Failed:       {len(failed)}",
        "",
        f"Duplicates removed: {duplicates_removed}",
        f"Average runtime:    {int(runtime_seconds // 60)}m {int(runtime_seconds % 60)}s",
    ]

    if failed:
        lines.extend(["", "Failed:"])
        for result in failed:
            lines.append(f"- {result.source_name} ({result.error})")

    return "\n".join(lines)
