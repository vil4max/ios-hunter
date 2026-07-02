# iOS Hunter Architecture

## Overview

```
GitHub Actions (hourly, Mon–Fri 08:00–18:00 Kyiv)
        │
   Swift Collector (~52 company sources)
        │ database/swift_export.json
   Python Pipeline
        │
   ┌────┴────┬──────────┬────────────┐
   │         │          │            │
 jobs.db  Activity   Health    Application Pack
   │         │          │            │
 Reports  Markdown   Markdown    Telegram
   │
 GitHub Pages (public analytics)
```

## Single database

**`database/jobs.db`** is the only source of truth. Swift does not write to SQLite — it only exports raw vacancies to `database/swift_export.json`. Python normalizes, deduplicates, stores history, and generates all reports.

SQLite is cached in GitHub Actions (not committed). JSON exports (`database/jobs.json`, `database/history.json`) are committed for readability.

## Pipeline

1. Swift collector fetches iOS vacancies from company career pages
2. Export deduplicated jobs to `database/swift_export.json`
3. Python reads Swift export + Teamtailor JSON feeds
4. Python upserts into `database/jobs.db`, detects New/Updated/Closed/Reopened
5. For actionable jobs above match threshold: cover letter + CV links → Telegram
6. Write Run Activity, Health, Market, Weekly, and Company reports
7. Auto-commit public artifacts to `main`

## Schedule

- **Collect:** every hour, Monday–Friday, 08:00–18:00 Europe/Kyiv
- **Weekly report:** Monday 09:00 Europe/Kyiv
- **AI summary (optional):** Monday 09:30, only if `OPENAI_API_KEY` or `GEMINI_API_KEY` is set

GitHub Actions cron uses UTC. Collect workflow uses `0 5-15 * * 1-5` (EEST, UTC+3). In winter (EET) local times shift by +1 hour.

## Modules

| Module | Role |
|--------|------|
| `Sources/JobHunter/` | Swift scrapers → `swift_export.json` |
| `collector/` | Python adapters (Swift export + Teamtailor feeds) |
| `parser/` | Normalize, dedup, diff, activity summary |
| `apply/` | Match score, cover letter, resume picker, application pack |
| `database/` | SQLite schema and repository (`jobs.db`) |
| `integrations/` | Telegram, weekly/companies reports, RSS |
| `crm/` | Application tracking |
| `statistics/` | Market intelligence |
| `ai/` | Optional AI weekly summary (off by default) |

## Design Principles

- Zero-cost hosting (GitHub + GitHub Pages)
- No backend server
- One SQLite database
- DOU/Djinni tracked manually via iPhone apps (not collected here)
- AI optional (rules-based matching first)
- Personal salary target: $4500–$6000 net (B1); aspirational $7000–$8000 with English 7–8 — informational only, not used to filter vacancies
