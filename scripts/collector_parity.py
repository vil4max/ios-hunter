from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collector.companies import collect_all
from collector.types import STATUS_FAILED
from database.source_health import (
    classify_degraded,
    default_baseline_path,
    load_baseline,
    save_baseline,
    update_baseline,
)
from parser.normalize import canonicalize_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Report Python collector coverage")
    parser.add_argument(
        "--company",
        action="append",
        default=[],
        help="Limit report to company name(s)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Persist the scanned-item counts of this run as the new baseline",
    )
    args = parser.parse_args()

    collect_result = collect_all()
    results = collect_result.source_results
    wanted = {name.lower() for name in args.company} if args.company else None

    baseline_path = default_baseline_path(ROOT)
    baseline = load_baseline(baseline_path)
    classify_degraded(results, baseline)
    if args.update_baseline:
        save_baseline(baseline_path, update_baseline(baseline, results))

    healthy = 0
    degraded = 0
    failed = 0
    total_jobs = 0
    by_company: Counter[str] = Counter()
    blind: list[str] = []

    for source in results:
        if wanted and source.source_name.lower() not in wanted:
            continue
        if source.status == STATUS_FAILED:
            failed += 1
            print(f"[FAIL] {source.source_name}: {source.error}")
            continue

        urls = {
            canonicalize_url(str(job.get("url") or ""))
            for job in source.jobs
            if job.get("url")
        }
        urls.discard("")
        total_jobs += len(urls)
        by_company[source.source_name] += len(urls)

        if source.status == "degraded":
            degraded += 1
            print(f"[DEGRADED] {source.source_name}: parsed 0 items · {source.response_ms}ms")
            continue

        healthy += 1
        if source.items_scanned == 0:
            blind.append(source.source_name)
        print(
            f"[OK] {source.source_name}: {len(urls)} url(s) "
            f"· scanned {source.items_scanned} · {source.response_ms}ms"
        )

    print(
        f"\nSummary: healthy={healthy} degraded={degraded} failed={failed} "
        f"unique_urls≈{total_jobs}"
    )
    if blind:
        print("\nNo baseline yet and parsed 0 items (verify manually):")
        for name in sorted(blind):
            print(f"  {name}")
    for company, count in by_company.most_common(30):
        if count:
            print(f"  {company}: {count}")
    return 1 if failed or degraded else 0


if __name__ == "__main__":
    raise SystemExit(main())
