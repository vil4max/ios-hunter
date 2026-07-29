from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from collector.bespoke import (
    collect_andersen,
    collect_ciklum,
    collect_dataart,
    collect_globallogic,
    collect_grid_dynamics,
    collect_infopulse,
    collect_intellias,
    collect_luxoft,
    collect_mwdn,
    collect_nix_html,
    collect_nortal,
    collect_onix,
    collect_rbi,
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
from collector.indeed import collect_indeed
from collector.generic import (
    collect_breezy,
    collect_html_regex,
    collect_recruitee,
    collect_smartrecruiters,
    collect_soup_links,
    collect_workable_widget,
    collect_wp_rest,
)
from collector.results import source_failed as _source_failed
from collector.results import source_ok as _source_ok
from collector.telegram_channels import collect_telegram_channels
from collector.types import CollectResult, SourceResult
from integrations.http_client import fetch_json, fetch_text
from parser.normalize import is_ios_job

_MAX_FEED_PAGES = 50
_HARDCODED_DOU_FEED_SLUGS: set[str] = set()
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
    collectors: list[Callable[[], SourceResult]] = []
    for row in companies:
        name = str(row["name"])
        slug = str(row["slug"])
        collectors.append(lambda name=name, slug=slug: collect_dou_company_feed(name, slug))
    return collectors


def collect_teamtailor(company: str, feed_url: str) -> SourceResult:
    started = time.perf_counter()
    try:
        jobs: list[dict[str, Any]] = []
        scanned = 0
        page_url: str | None = feed_url
        visited: set[str] = set()
        while page_url and page_url not in visited and len(visited) < _MAX_FEED_PAGES:
            visited.add(page_url)
            payload = fetch_json(page_url)
            items = payload.get("jobs", payload.get("items", payload if isinstance(payload, list) else []))
            scanned += len(items)
            for item in items:
                title = str(item.get("title", ""))
                if not is_ios_job(title):
                    continue
                jobs.append(
                    {
                        "company": company,
                        "title": title,
                        "url": item.get("url") or item.get("links", {}).get("careersite-job-url", ""),
                        "source": "company",
                        "source_job_id": item.get("id") or item.get("job_id"),
                        "description": item.get("body") or item.get("description"),
                        "location": (item.get("location") or {}).get("city")
                        if isinstance(item.get("location"), dict)
                        else item.get("location"),
                    }
                )
            next_url = payload.get("next_url") if isinstance(payload, dict) else None
            page_url = str(next_url) if next_url else None
        return _source_ok(company, feed_url, jobs, started, scanned=scanned)
    except Exception as error:  # noqa: BLE001
        return _source_failed(company, feed_url, error, started)


def collect_greenhouse(company: str, board_slug: str) -> SourceResult:
    started = time.perf_counter()
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs?content=true"
    try:
        payload = fetch_json(url)
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
        jobs: list[dict[str, Any]] = []
        for item in items:
            title = str(item.get("title", ""))
            if not is_ios_job(title):
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": item.get("absolute_url") or item.get("url") or "",
                    "source": "company",
                    "source_job_id": item.get("id"),
                    "description": item.get("content"),
                    "location": (item.get("location") or {}).get("name")
                    if isinstance(item.get("location"), dict)
                    else item.get("location"),
                    "updated_at": item.get("updated_at"),
                }
            )
        return _source_ok(company, url, jobs, started, scanned=len(items))
    except Exception as error:  # noqa: BLE001
        return _source_failed(company, url, error, started)


def collect_ashby(company: str, board_slug: str) -> SourceResult:
    started = time.perf_counter()
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board_slug}"
    try:
        payload = fetch_json(url)
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
        jobs: list[dict[str, Any]] = []
        for item in items:
            title = str(item.get("title", ""))
            if not is_ios_job(title):
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": item.get("jobUrl") or item.get("applyUrl") or "",
                    "source": "company",
                    "source_job_id": item.get("id") or item.get("jobId"),
                    "description": item.get("descriptionPlain") or item.get("descriptionHtml"),
                    "location": item.get("location"),
                }
            )
        return _source_ok(company, url, jobs, started, scanned=len(items))
    except Exception as error:  # noqa: BLE001
        return _source_failed(company, url, error, started)


def collect_lever(company: str, board_slug: str) -> SourceResult:
    started = time.perf_counter()
    url = f"https://api.lever.co/v0/postings/{board_slug}?mode=json"
    try:
        payload = fetch_json(url)
        items = payload if isinstance(payload, list) else []
        jobs: list[dict[str, Any]] = []
        for item in items:
            title = str(item.get("text", ""))
            if not is_ios_job(title):
                continue
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": item.get("hostedUrl") or item.get("applyUrl") or "",
                    "source": "company",
                    "source_job_id": item.get("id"),
                    "description": item.get("descriptionPlain") or item.get("description"),
                    "location": item.get("categories", {}).get("location"),
                    "updated_at": item.get("createdAt"),
                }
            )
        return _source_ok(company, url, jobs, started, scanned=len(items))
    except Exception as error:  # noqa: BLE001
        return _source_failed(company, url, error, started)


def collect_workable_jobs_md(company: str, account_slug: str) -> SourceResult:
    """Parse the Workable markdown board.

    Workable serves a table only for small boards; larger accounts get a
    "How to Search" document instead, which yields no rows at all. Prefer
    ``collect_workable_widget`` and keep this as a secondary source.
    """
    started = time.perf_counter()
    url = f"https://apply.workable.com/{account_slug}/jobs.md"
    try:
        text = fetch_text(url)
        jobs: list[dict[str, Any]] = []
        scanned = 0
        for line in text.splitlines():
            if not line.startswith("| "):
                continue
            if " Title " in line or line.startswith("|-------"):
                continue
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            if len(parts) < 7:
                continue
            scanned += 1
            title = parts[0]
            if not is_ios_job(title):
                continue
            location = parts[2]
            details = parts[6]
            match = re.search(r"\((https?://[^)]+)\)", details)
            job_url = match.group(1) if match else ""
            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "url": job_url,
                    "source": "company",
                    "location": location,
                }
            )
        return _source_ok(company, url, jobs, started, scanned=scanned)
    except Exception as error:  # noqa: BLE001
        return _source_failed(company, url, error, started)


def _python_collectors() -> list[Callable[[], SourceResult]]:
    return [
        lambda: collect_wp_rest("Leobit", "https://leobit.com/wp-json/wp/v2/vacancies?per_page=100"),
        collect_andersen,
        collect_nix_html,
        lambda: collect_wp_rest("SPD Technology", "https://spd.tech/wp-json/wp/v2/job-listings?per_page=100"),
        lambda: collect_soup_links(
            "Dev.Pro",
            "https://career.dev.pro/open-positions/",
            base_url="https://career.dev.pro/",
            selector="a.position-row",
            title_selector=".position-title h3",
            location_selector=".position-info span",
            pagination_selector="a[href*='/open-positions/page/']",
        ),
        collect_intellias,
        collect_mwdn,
        collect_onix,
        lambda: collect_soup_links(
            "QArea",
            "https://qarea.com/careers",
            base_url="https://qarea.com/",
            selector="a.vacancies-item",
            title_selector=".vacancies-item-title .item-title",
        ),
        lambda: collect_soup_links(
            "Exoft",
            "https://www.exoft.net/career/",
            base_url="https://www.exoft.net/",
            selector="a[href*='/career/']",
            skip_exact={"https://www.exoft.net/career/", "https://www.exoft.net/career"},
        ),
        lambda: collect_soup_links(
            "Softjourn",
            "https://softjourn.com/careers",
            base_url="https://softjourn.com/",
            selector="a[href*='/careers/vacancies/']",
            skip_hrefs={"/careers/vacancies", "/careers/vacancies/"},
        ),
        lambda: collect_soup_links(
            "ELEKS",
            "https://careers.eleks.com/vacancies/",
            base_url="https://careers.eleks.com/",
            selector="a.vacancy-item",
            title_selector=".vacancy-item__title",
        ),
        lambda: collect_soup_links(
            "Agiliway",
            "https://www.agiliway.com/career/",
            base_url="https://www.agiliway.com/",
            selector="a[href*='/careers/']",
            skip_hrefs={"/careers/", "/career/"},
        ),
        lambda: collect_greenhouse("Innovecs", "innovecs"),
        lambda: collect_teamtailor("Levi9", "https://jobs.ua.levi9.com/jobs.json"),
        lambda: collect_teamtailor("Avenga", "https://career.avenga.com/jobs.json"),
        lambda: collect_html_regex(
            "CHI Software",
            "https://chisw.com/careers/vacancies/",
            "https://chisw.com/",
            r"https://chisw\.com/vacancies/([a-z0-9-]+)/",
        ),
        lambda: collect_html_regex(
            "Sombra",
            "https://sombrainc.com/careers",
            "https://sombrainc.com/",
            r"https://sombrainc\.com/careers/(?!page|feed)([a-z0-9-]+(?:-[a-z0-9-]+)*)",
        ),
        lambda: collect_html_regex(
            "Vakoms",
            "https://vakoms.com/careers",
            "https://vakoms.com/",
            r"/careers/([a-z0-9-]+(?:-[a-z0-9-]+)+)",
        ),
        lambda: collect_html_regex(
            "Inoxoft",
            "https://inoxoft.com/vacancies/",
            "https://inoxoft.com/",
            r"https://inoxoft\.com/vacancies/([a-z0-9-]+)/",
        ),
        lambda: collect_html_regex(
            "Otakoyi",
            "https://otakoyi.software/careers/",
            "https://otakoyi.software/",
            r"/careers/([a-z0-9-]+(?:-[a-z0-9-]+)+)",
        ),
        lambda: collect_html_regex(
            "AltexSoft",
            "https://www.altexsoft.com/careers/",
            "https://www.altexsoft.com/",
            r"/vacancy/([a-z0-9]+(?:-[a-z0-9]+)*)/",
        ),
        lambda: collect_html_regex(
            "Computools",
            "https://computools.com/careers/",
            "https://computools.com/",
            r"https://computools\.com/career/([a-z0-9-]+)/",
        ),
        lambda: collect_html_regex(
            "Zfort",
            "https://www.zfort.com/company/careers",
            "https://www.zfort.com/",
            r'<h3 class="chess-item-title">([^<]+)</h3>',
            title_group=1,
            use_list_url_as_job_url=True,
        ),
        collect_nortal,
        lambda: collect_wp_rest("Yalantis", "https://yalantis.ua/wp-json/wp/v2/vacancies?per_page=100"),
        lambda: collect_html_regex(
            "Xenoss",
            "https://xenoss.io/careers",
            "https://xenoss.io/",
            r"https://xenoss\.io/careers/([a-z0-9-]+)/?",
        ),
        lambda: collect_html_regex(
            "Inverita",
            "https://inveritasoft.com/vacancies",
            "https://inveritasoft.com/",
            r'<h3 class="font-25">\s*([^<]+?)\s*</h3>[\s\S]*?href="(https://inveritasoft\.com/article-[^"]+)"',
            url_group=2,
            title_group=1,
        ),
        lambda: collect_soup_links(
            "Devlight",
            "https://devlight.io/careers/",
            base_url="https://devlight.io/",
            selector="a[href*='/careers/']",
            skip_exact={"https://devlight.io/careers/", "https://devlight.io/careers"},
        ),
        collect_ciklum,
        collect_sigma,
        collect_infopulse,
        collect_softserve,
        collect_globallogic,
        collect_luxoft,
        lambda: collect_breezy("Genesis", "gen-tech.breezy.hr"),
        lambda: collect_breezy("BetterMe", "betterme.breezy.hr"),
        collect_zone3000,
        lambda: collect_smartrecruiters("Miratech", "MiratechGroup"),
        lambda: collect_smartrecruiters("Gameloft", "Gameloft"),
        lambda: collect_breezy("Star", "star.breezy.hr"),
        lambda: collect_lever("Ajax Systems", "ajax"),
        lambda: collect_ashby("Preply", "preply"),
        lambda: collect_teamtailor("UPSTARS", "https://career.upstars.com/jobs.json"),
        lambda: collect_greenhouse("Amdaris", "amdaris"),
        lambda: collect_soup_links(
            "Petcube",
            "https://petcube.com/careers/",
            base_url="https://petcube.com/",
            selector="a[href^='/careers/']",
            skip_exact={
                "https://petcube.com/careers/",
                "https://petcube.com/careers",
            },
        ),
        lambda: collect_soup_links(
            "Gismart",
            "https://gismart.com/careers/",
            base_url="https://gismart.com/",
            selector="a[href*='/vacancy/']",
        ),
        lambda: collect_soup_links(
            "Stfalcon",
            "https://stfalcon.com/en/jobs",
            base_url="https://stfalcon.com/",
            selector='a[href*="/jobs/job/"]',
            skip_hrefs={"#more"},
        ),
        *_dou_collectors_from_seed(),
        lambda: collect_soup_links(
            "CS Ltd.",
            "https://csltd.com.ua/career/",
            base_url="https://csltd.com.ua/",
            selector='a[href*="/career/"]',
            skip_exact={
                "https://csltd.com.ua/career/",
                "https://csltd.com.ua/career",
                "https://csltd.com.ua/ru/career/",
                "https://csltd.com.ua/en/career/",
            },
        ),
        lambda: collect_html_regex(
            "Software MacKiev",
            "https://www.mackiev.com/",
            "https://www.mackiev.com/",
            r'href="([^"]*(?:career|job|vacanc)[^"]*)"',
            allow_bot_wall=True,
        ),
        lambda: collect_html_regex(
            "Softline",
            "https://softline.com/",
            "https://softline.com/",
            r'href="([^"]*(?:career|job|vacanc)[^"]*)"',
            allow_bot_wall=True,
        ),
        lambda: collect_soup_links(
            "MacPaw",
            "https://macpaw.com/careers",
            base_url="https://macpaw.com/",
            selector="a[href^='/careers/']",
            skip_exact={
                "https://macpaw.com/careers",
                "https://macpaw.com/careers/",
                "https://macpaw.com/careers-all",
            },
        ),
        collect_dataart,
        lambda: collect_workable_widget("Intellectsoft", "intellectsoft"),
        collect_grid_dynamics,
        collect_epam,
        collect_rbi,
        lambda: collect_greenhouse("Readdle", "readdle70"),
        lambda: collect_greenhouse("N-iX", "nix"),
        lambda: collect_lever("ELEKS", "eleks"),
        lambda: collect_workable_widget("Globaldev Group", "globaldevgroup"),
        lambda: collect_workable_widget("Intetics", "intetics-2"),
        lambda: collect_workable_widget("Intersog", "intersog-na"),
        lambda: collect_workable_widget("SupportYourApp", "supportyourapp"),
        lambda: collect_lever("Kyivstar.Tech", "kyivstar"),
        lambda: collect_greenhouse("Netcracker", "netcracker"),
        lambda: collect_greenhouse("SQUAD", "squad"),
        lambda: collect_workable_widget("Trinetix", "trinetix"),
        lambda: collect_recruitee("Playrix", "playrix"),
        lambda: collect_smartrecruiters("Playtech", "playtech"),
        collect_djinni,
        collect_indeed,
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
