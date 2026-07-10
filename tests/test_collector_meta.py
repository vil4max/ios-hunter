from __future__ import annotations

import json

from collector.companies import collect_all, load_swift_collector_meta, load_swift_export


def test_load_swift_collector_meta_reads_meta_block(tmp_path) -> None:
    export_path = tmp_path / "swift_export.json"
    export_path.write_text(
        json.dumps(
            {
                "meta": {
                    "sources_total": 53,
                    "sources_failed": 1,
                    "failed_companies": ["EPAM"],
                },
                "jobs": [{"company": "Acme", "title": "iOS Dev", "url": "https://example.com"}],
            }
        ),
        encoding="utf-8",
    )

    meta = load_swift_collector_meta(export_path)
    jobs = load_swift_export(export_path)

    assert meta is not None
    assert meta.sources_total == 53
    assert meta.sources_ok == 52
    assert meta.failed_companies == ["EPAM"]
    assert len(jobs) == 1


def test_collect_all_returns_swift_meta(tmp_path) -> None:
    export_path = tmp_path / "swift_export.json"
    export_path.write_text(
        json.dumps(
            {
                "meta": {"sources_total": 2, "sources_failed": 0, "failed_companies": []},
                "jobs": [{"company": "Acme", "title": "iOS Dev", "url": "https://example.com"}],
            }
        ),
        encoding="utf-8",
    )

    result = collect_all(export_path)

    assert result.swift_meta is not None
    assert result.swift_meta.sources_total == 2
    assert any(source.source_id == "swift-export" for source in result.source_results)
