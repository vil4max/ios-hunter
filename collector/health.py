from __future__ import annotations

from collector.types import SourceResult, SwiftCollectorMeta


def render_health_report(
    results: list[SourceResult],
    runtime_seconds: float,
    duplicates_removed: int,
    swift_meta: SwiftCollectorMeta | None = None,
) -> str:
    feed_results = [result for result in results if result.source_id != "swift-export"]
    feed_failed = [result for result in feed_results if result.status == "failed"]
    feed_ok = len(feed_results) - len(feed_failed)

    lines = [
        "Collector Health",
        "",
    ]

    if swift_meta and swift_meta.sources_total > 0:
        lines.append(f"Companies:    {swift_meta.sources_ok}/{swift_meta.sources_total} OK")
    if feed_results:
        lines.append(f"Direct feeds: {feed_ok}/{len(feed_results)} OK")
    if not swift_meta and not feed_results:
        total = len(results)
        failed = [result for result in results if result.status == "failed"]
        lines.extend(
            [
                f"Sources:      {total}",
                f"Healthy:      {total - len(failed)}",
                f"Failed:       {len(failed)}",
            ]
        )

    if feed_failed:
        lines.extend(["", "Failed feeds:"])
        for result in feed_failed:
            lines.append(f"- {result.source_name} ({result.error})")

    if swift_meta and swift_meta.failed_companies:
        lines.extend(["", "Failed companies:"])
        for company in swift_meta.failed_companies:
            lines.append(f"- {company}")

    lines.extend(
        [
            "",
            f"Duplicates removed: {duplicates_removed}",
            f"Average runtime:    {int(runtime_seconds // 60)}m {int(runtime_seconds % 60)}s",
        ]
    )

    return "\n".join(lines)
