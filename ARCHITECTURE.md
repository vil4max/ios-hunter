# iOS Hunter Architecture

Career Agent target: `docs/architecture/career-agent.md`. ADR: `docs/adr/0001-career-agent-architecture.md`.

## Overview

```
GitHub Actions (Kyiv 09/12/15/18, ubuntu)
        │
   Python collectors (company pages, ATS, DOU, Telegram)
        │
   Normalize → Deduplicate → Project Sync (+ seen.json dual-write) → Telegram on new

GitHub Actions (daily 04:00 UTC, incl. weekends)
        │
   Vacancy liveness (active Project URLs) → archive Role closed → Telegram status
```

## Pipeline

1. Python collectors fetch iOS / Swift vacancies from career pages, ATS boards, DOU, and Telegram.
2. Vacancies are normalized and filtered to iOS / Swift titles (or descriptions) and relevant locations (Ukraine + global remote).
3. In-run deduplication collapses identical identity keys and same company+title roles.
4. When Sync is enabled, Project Sync creates Issue + Project item (Inbox) for new Canonical-URLs.
5. Collect-slot Telegram sends an Inbox +N alert with vacancy details when something new lands.
6. Collect workflow commits `database/seen.json` when it changes (`[skip ci]`) during dual-write.

## State

**GitHub Project** is the operational source of truth for Status after Sync is enabled.

**`database/seen.json`** remains a dual-write notify/sync journal until cutover (`docs/migration-plan.md`).

## Modules

| Module | Role |
|--------|------|
| `collector/` | Company/ATS/DOU/Telegram collectors |
| `parser/` | Normalize, iOS filter, geo filter, dedupe |
| `config/` | Project + Sync settings from env |
| `project_sync/` | Issues + Projects V2 GraphQL |
| `planner/` | Daily work from Project cards |
| `reporter/` | Collect-slot short alert + daily vacancy-liveness Telegram |
| `analytics/` | Pipeline summary helpers |
| `database/seen.py` | Dual-write seen store |
| `scripts/run_pipeline.py` | Collect → sync → Telegram |
| `scripts/run_vacancy_liveness.py` | Daily closed-URL check → archive → Telegram |
| `scripts/run_daily_report.py` | Optional Project plan counts (Actions log) |
| `scripts/seed_project_from_seen.py` | Seed Archived from seen.json |
| `scripts/collector_parity.py` | Collector health report |

## Schedule

- **Collect + IMAP:** Kyiv 09/12/15/18 via `hourly-trigger.yml` (Collect Schedule Trigger) → Collect iOS Jobs + IMAP Recruiter Poll
- **Daily email:** same trigger at Kyiv 18:00 → Daily Email Report (final slot)
- **Vacancy liveness:** `vacancy-liveness.yml` daily 04:00 UTC incl. weekends
- **CI:** on push/PR to `main`
