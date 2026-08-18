from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from collector.bespoke import (
    collect_andersen,
    collect_ciklum,
    collect_dataart,
    collect_globallogic,
    collect_grid_dynamics,
    collect_infopulse,
    collect_intellias,
    collect_luxoft,
    collect_nix_html,
    collect_sigma,
    collect_softserve,
    collect_zone3000,
)
from collector.dou import collect_dou_company_feed, collect_dou_ios_rss
from collector.dou_catalog import (
    DEFAULT_SEED_FEED_LIMIT,
    companies_for_collect,
    default_seed_path,
    load_seed,
)
from collector.djinni import collect_djinni
from collector.epam import collect_epam
from collector.telegram_channels import collect_telegram_channels
from collector.types import CollectResult, SourceResult

_HARDCODED_DOU_FEED_SLUGS: set[str] = {
    "andersen",
    "ciklum",
    "dataart",
    "epam-systems",
    "globallogic",
    "grid-dynamics",
    "intellias",
    "luxoft",
    "n-ix",
    "sigma-software",
    "softserve",
    "tieto",
    "zone3000",
}
_DOU_SERVICE_SLUGS = frozenset(
    {
        "allstars-it",
        "avenga",
        "capgemini-engineering",
        "eleks",
        "geeksforless",
        "levi9",
        "miratech",
        "spd-technology",
        "svitla-systems-inc",
        "trinetix",
    }
)
_REPO_ROOT = Path(__file__).resolve().parents[1]


def _seed_feed_limit() -> int | None:
    raw = os.environ.get("DOU_SEED_FEED_LIMIT", "").strip()
    if raw == "":
        return DEFAULT_SEED_FEED_LIMIT
    if raw.lower() in {"none", "all", "0"}:
        return None
    return max(0, int(raw))


def _dou_collectors_from_seed(
    *,
    seed_path: Path | None = None,
    skip_slugs: set[str] | None = None,
    allowed_slugs: frozenset[str] | None = _DOU_SERVICE_SLUGS,
) -> list[Callable[[], SourceResult]]:
    path = seed_path or default_seed_path(_REPO_ROOT)
    seed = load_seed(path)
    skip = set(_HARDCODED_DOU_FEED_SLUGS)
    if skip_slugs:
        skip |= {slug.lower() for slug in skip_slugs}
    companies = companies_for_collect(
        seed,
        skip_slugs=skip,
        feed_limit=_seed_feed_limit(),
    )
    if allowed_slugs is not None:
        companies = [row for row in companies if str(row["slug"]).lower() in allowed_slugs]
    collectors: list[Callable[[], SourceResult]] = []
    for row in companies:
        name = str(row["name"])
        slug = str(row["slug"])
        collectors.append(lambda name=name, slug=slug: collect_dou_company_feed(name, slug))
    return collectors


def _python_collectors() -> list[Callable[[], SourceResult]]:
    return [
        collect_epam,
        collect_softserve,
        collect_globallogic,
        collect_luxoft,
        collect_ciklum,
        collect_dataart,
        collect_intellias,
        collect_nix_html,
        collect_sigma,
        collect_infopulse,
        collect_andersen,
        collect_zone3000,
        collect_grid_dynamics,
        *_dou_collectors_from_seed(),
        collect_djinni,
        collect_dou_ios_rss,
    ]


def collect_all(*, max_workers: int = 12) -> CollectResult:
    results: list[SourceResult] = []
    collectors = _python_collectors()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(collector) for collector in collectors]
        for future in as_completed(futures):
            results.append(future.result())

    results.extend(collect_telegram_channels())
    return CollectResult(source_results=results)
