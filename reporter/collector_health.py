from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from parser.normalize import (
    Vacancy, ai_requirement_blockers, has_ai_job_details, is_ai_augmented_job,
    is_location_eligible, is_primary_ios_role,
)


def rejection_counts(vacancies: list[Vacancy]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for vacancy in vacancies:
        reasons = []
        if not is_location_eligible(vacancy.location, vacancy.remote):
            reasons.append("location")
        if not is_primary_ios_role(vacancy.title):
            if not is_ai_augmented_job(vacancy.title, vacancy.description):
                reasons.append("outside_primary_ios_or_ai")
            else:
                if not has_ai_job_details(vacancy.title, vacancy.description):
                    reasons.append("ai_details_missing")
                if ai_requirement_blockers(vacancy.title, vacancy.description or ""):
                    reasons.append("ai_requirements")
        for reason in reasons:
            counts[reason] = counts.get(reason, 0) + 1
    return counts


def safe_error(value: str) -> str:
    # Artifact content is not covered by Actions' console secret masking.
    for name, secret in os.environ.items():
        if len(secret) >= 4 and re.search(r"TOKEN|SECRET|PASSWORD|PASS$|API_KEY|API_HASH|SESSION", name):
            value = value.replace(secret, "[redacted]")
    value = re.sub(r"https?://\S+", "[url]", value)
    return value[:500]


def write_collect_diagnostics(report: dict[str, Any], *, summary: bool = False) -> None:
    target = os.environ.get("COLLECT_DIAGNOSTICS_PATH")
    if target:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY") if summary else None
    if not summary_path:
        return
    lines = ["## Vacancy collection", "", f"Status: **{report.get('status', 'unknown')}**", ""]
    for key, value in report.get("counts", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "| Source | Status | Scanned | Normalized | Inbox eligible | Reason |",
                  "|---|---|---:|---:|---:|---|"])
    for source in report.get("sources", []):
        def cell(value: object) -> str:
            return str(value).replace("|", " / ").replace("\n", " ").replace("<", "&lt;")
        lines.append("| " + " | ".join(cell(source.get(key, "")) for key in (
            "name", "status", "scanned", "normalized", "inbox_eligible", "reason",
        )) + " |")
    with Path(summary_path).open("a", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
