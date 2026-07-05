# iOS Hunter Architecture

## Overview

```
GitHub Actions (hourly Sun 18:00–21:00 + Mon–Fri 08:00–18:00 Kyiv)
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
```

## Single database

**`database/jobs.db`** is the only source of truth. Swift does not write to SQLite — it only exports raw vacancies to `database/swift_export.json`. Python normalizes, deduplicates, stores history, and generates reports.

SQLite is cached in GitHub Actions (not committed). Job data and history stay in the cache only.

## Pipeline

1. Swift collector fetches iOS vacancies from company career pages
2. Export deduplicated jobs to `database/swift_export.json`
3. Python reads Swift export + Teamtailor JSON feeds
4. Python upserts into `database/jobs.db`, detects New/Updated/Closed/Reopened
5. For actionable jobs above match threshold: Job Intelligence (or rules fallback) → Telegram
6. Write Run Activity, Health, Market, Weekly, and Company reports
7. Auto-commit reports to `main` (private repository)

## Schedule

- **Collect:** Sunday 18:00–21:00 + Monday–Friday 08:00–18:00 Europe/Kyiv
- **Weekly report:** Monday 09:00 Europe/Kyiv
- **AI summary (optional):** Monday 09:30, only if `OPENAI_API_KEY` or `GEMINI_API_KEY` is set

GitHub Actions cron uses UTC. Collect: `0 15-18 * * 0` (Sun EEST) and `0 5-15 * * 1-5` (weekdays). In winter (EET) local times shift by +1 hour.

## Modules

| Module | Role |
|--------|------|
| `Sources/JobHunter/` | Swift scrapers → `swift_export.json` |
| `collector/` | Python adapters (Swift export + Teamtailor feeds) |
| `parser/` | Normalize, dedup, diff, activity summary |
| `apply/` | Match score, Job Intelligence, application pack |
| `database/` | SQLite schema and repository (`jobs.db`) |
| `integrations/` | Telegram, weekly/companies reports |
| `crm/` | Application tracking |
| `statistics/` | Market intelligence |
| `ai/` | Optional AI weekly summary and Job Intelligence |

## Design Principles

- Zero-cost hosting (GitHub Actions + private repo)
- No backend server
- One SQLite database
- Telegram as the primary output channel
- DOU/Djinni tracked manually via iPhone apps (not collected here)
- AI optional (rules-based matching first)
- Compensation preferences are kept private and are not part of vacancy filtering
