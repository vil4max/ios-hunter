from __future__ import annotations

import csv
import io
import re
import time
import xml.etree.ElementTree as ET
from html import unescape
from typing import Any
from urllib.parse import quote

import requests

from collector.dou_careers import (
    collect_jobs_from_career_site,
    extract_company_site_url,
    write_career_sites_report,
)
from collector.types import SourceResult

TOP50_PAGE_URL = "https://jobs.dou.ua/top50/"
TOP50_CSV_BASE_URL = "https://s.dou.ua/files/top50/"
TOP50_LIST_URL = "https://jobs.dou.ua/top50/"
IOS_FEED_URL = "https://jobs.dou.ua/vacancies/feeds/?search=iOS"
SWIFT_FEED_URL = "https://jobs.dou.ua/vacancies/feeds/?search=Swift"
USER_AGENT = "ios-hunter/2.0 (+https://github.com/)"

VACANCY_LINK_PATTERN = re.compile(
    r'<a class="vt" href="(https://jobs\.dou\.ua/companies/[^"]+/vacancies/(\d+)/)"[^>]*>\s*([^<]+)</a>',
    re.IGNORECASE,
)
COMPANY_SLUG_PATTERN = re.compile(
    r'href="https://jobs\.dou\.ua/companies/([^/]+)/vacancies/"'
)
TOP50_CSV_PATTERN = re.compile(r"top50-\d{4}-\d{2}_v\d+\.csv")
COMPANY_FROM_TITLE_PATTERN = re.compile(r" в (.+?)(?:,|$)")

SLUG_OVERRIDES: dict[str, str] = {
    "EPAM Ukraine": "epam-systems",
    "SoftServe": "softserve",
    "GlobalLogic Ukraine": "globallogic",
    "Ajax Systems": "ajax-systems",
    "Genesis": "genesis-technology-partners",
    "DXC Luxoft": "luxoft",
    "Evoplay": "evoplay",
    "ZONE3000": "zone3000",
    "DataArt": "dataart",
    "Intellias": "intellias",
    "Ciklum": "ciklum",
    "N-iX": "n-ix",
    "Sigma Software": "sigma-software",
    "ELEKS": "eleks",
    "Tietoevry Create Ukraine": "tietoevry",
    "FRACTAL": "fractal-analytics",
    "SKELAR": "skelar",
    "Autodoc Ukraine": "autodoc",
    "Nova Digital": "nova-digital",
    "Capgemini Engineering": "capgemini-engineering",
    "TemaBit Fozzy Group": "fozzy",
    "ALLSTARSIT": "allstars-it",
    "EVO": "evo",
    "King Group": "king-group",
    "Avenga": "avenga",
    "Intecracy Group": "intecracy-group-consortium",
    "ONSEO": "onseo",
    "MODUS X": "modus-x",
    "MEGOGO": "megogonet-",
    "Uklon": "uklon",
    "mono": "mono",
    "UPSTARS": "upstars",
    "Metinvest Digital": "metinvest-digital",
    "Playtech": "playtech",
    "Wix": "wix",
    "Binotel": "binotel",
    "Trinetix": "trinetix",
    "Netcracker": "netcracker",
    "Grid Dynamics Group": "grid-dynamics",
    "Plarium": "plarium",
    "Kyivstar.Tech": "kyivstar-tech",
    "Room 8 Group": "room-8-group",
    "Playrix": "playrix",
    "SPD Technology": "spd-technology",
    "Svitla Systems": "svitla-systems-inc",
    "ISD": "isd",
    "GeeksForLess": "geeksforless",
    "SQUAD": "squad",
    "Ubisoft Ukraine": "ubisoft",
}


def _is_ios_title(title: str) -> bool:
    lowered = title.lower()
    return "ios" in lowered or "swift" in lowered


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _parse_top50_date(value: str) -> tuple[int, int]:
    month, year = value.split("-")
    return int(year), int(month)


def _fetch_text(url: str, session: requests.Session) -> str:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def discover_top50_csv_filename(session: requests.Session) -> str:
    page = _fetch_text(TOP50_PAGE_URL, session)
    scripts = re.findall(r"built\.v\d+\.[a-f0-9]+\.js", page)
    for script in reversed(scripts):
        bundle = _fetch_text(f"https://s.dou.ua/build/{script}", session)
        match = TOP50_CSV_PATTERN.search(bundle)
        if match:
            return match.group(0)
    raise ValueError("DOU top50 CSV filename not found")


def load_top50_companies(session: requests.Session) -> list[str]:
    filename = discover_top50_csv_filename(session)
    csv_text = _fetch_text(f"{TOP50_CSV_BASE_URL}{filename}", session)
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    latest_date = max((row["date"] for row in rows if row.get("date")), key=_parse_top50_date)
    companies = [
        row["company"].strip()
        for row in rows
        if row.get("date") == latest_date and int(row.get("rate", "0")) <= 50
    ]
    companies.sort(key=lambda name: name.lower())
    return companies


def _build_company_matchers(companies: list[str]) -> list[tuple[str, str]]:
    matchers: list[tuple[str, str]] = []
    seen: set[str] = set()
    for company in companies:
        variants = {company}
        variants.add(re.sub(r"\b(Ukraine|Group|Technology|Systems|Digital)\b", "", company, flags=re.I).strip())
        variants.add(company.split()[0])
        for variant in variants:
            normalized = _normalize_name(variant)
            if normalized and normalized not in seen:
                seen.add(normalized)
                matchers.append((normalized, company))
    matchers.sort(key=lambda item: len(item[0]), reverse=True)
    return matchers


def match_top50_company(raw_company: str, matchers: list[tuple[str, str]]) -> str | None:
    normalized = _normalize_name(raw_company)
    if not normalized:
        return None
    for key, company in matchers:
        if normalized == key or key in normalized or normalized in key:
            return company
    return None


def resolve_company_slug(company: str, session: requests.Session) -> str | None:
    override = SLUG_OVERRIDES.get(company)
    if override:
        return override

    response = session.get(
        f"https://jobs.dou.ua/vacancies/?search={quote(company)}",
        timeout=30,
    )
    response.raise_for_status()
    slugs = COMPANY_SLUG_PATTERN.findall(response.text)
    if not slugs:
        return None
    return slugs[0]


def _parse_company_vacancies(html: str, company: str) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for match in VACANCY_LINK_PATTERN.finditer(html):
        url, vacancy_id, title = match.group(1), match.group(2), unescape(match.group(3).strip())
        if not _is_ios_title(title):
            continue
        jobs.append(
            {
                "company": company,
                "title": title,
                "url": url,
                "source": "dou",
                "source_job_id": vacancy_id,
            }
        )
    return jobs


def _parse_rss_items(xml_text: str, matchers: list[tuple[str, str]]) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    jobs: list[dict[str, Any]] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        if not _is_ios_title(title):
            continue
        company_match = COMPANY_FROM_TITLE_PATTERN.search(title)
        if not company_match:
            continue
        company = match_top50_company(company_match.group(1).strip(), matchers)
        if company is None:
            continue
        vacancy_id_match = re.search(r"/vacancies/(\d+)/", link)
        jobs.append(
            {
                "company": company,
                "title": title.split(" в ", 1)[0].strip(),
                "url": link.split("?", 1)[0],
                "source": "dou",
                "source_job_id": vacancy_id_match.group(1) if vacancy_id_match else None,
            }
        )
    return jobs


def collect_dou_top50() -> SourceResult:
    started = time.perf_counter()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    try:
        companies = load_top50_companies(session)
        matchers = _build_company_matchers(companies)
        jobs_by_url: dict[str, dict[str, Any]] = {}
        career_sites: list[dict[str, str]] = []

        for company in companies:
            slug = resolve_company_slug(company, session)
            if not slug:
                continue

            profile_url = f"https://jobs.dou.ua/companies/{slug}/"
            profile_response = session.get(profile_url, timeout=30)
            if profile_response.status_code == 200:
                career_url = extract_company_site_url(profile_response.text)
                if career_url:
                    career_sites.append(
                        {
                            "company": company,
                            "dou_url": profile_url,
                            "career_url": career_url,
                        }
                    )
                    for job in collect_jobs_from_career_site(company, career_url, session):
                        jobs_by_url[job["url"]] = job

            vacancies_url = f"https://jobs.dou.ua/companies/{slug}/vacancies/"
            response = session.get(vacancies_url, timeout=30)
            if response.status_code != 200:
                continue
            for job in _parse_company_vacancies(response.text, company):
                jobs_by_url[job["url"]] = job

        write_career_sites_report(career_sites)

        for feed_url in (IOS_FEED_URL, SWIFT_FEED_URL):
            feed_text = _fetch_text(feed_url, session)
            for job in _parse_rss_items(feed_text, matchers):
                jobs_by_url[job["url"]] = job

        jobs = list(jobs_by_url.values())
        elapsed = int((time.perf_counter() - started) * 1000)
        return SourceResult(
            source_id="dou-top50",
            source_name="DOU Top 50",
            source_url=TOP50_LIST_URL,
            jobs=jobs,
            status="healthy",
            error=None,
            response_ms=elapsed,
        )
    except Exception as error:  # noqa: BLE001
        elapsed = int((time.perf_counter() - started) * 1000)
        return SourceResult(
            source_id="dou-top50",
            source_name="DOU Top 50",
            source_url=TOP50_LIST_URL,
            jobs=[],
            status="failed",
            error=str(error),
            response_ms=elapsed,
        )
