# iOS Hunter Architecture

Career Agent target: `docs/architecture/career-agent.md`. ADR: `docs/adr/0001-career-agent-architecture.md`.

## Overview

```
GitHub Actions (hourly)
        │
   Swift Collector (company career pages)
        │ database/swift_export.json
   Python Pipeline
        │
   Normalize → Deduplicate → Project Sync (+ seen.json dual-write) → Telegram hourly
Daily Actions → Planner (Project read) → Telegram dashboard
```

## Pipeline

1. Swift scrapers fetch iOS / Swift vacancies and write `database/swift_export.json`.
2. Python loads the Swift export plus additional Python sources.
3. Vacancies are normalized and filtered to iOS / Swift titles (or descriptions).
4. In-run deduplication collapses identical identity keys and same company+title roles.
5. When Sync is enabled, Project Sync creates Issue + Project item (Inbox) for new Canonical-URLs.
6. Hourly Telegram sends a short Inbox +N alert (no vacancy list). Daily report is a separate workflow.
7. Collect workflow commits `database/seen.json` when it changes (`[skip ci]`) during dual-write.

## State

**GitHub Project** is the operational source of truth for Status after Sync is enabled.

**`database/seen.json`** remains a dual-write notify/sync journal until cutover (`docs/migration-plan.md`).

## Modules

| Module | Role |
|--------|------|
| `Sources/JobHunter/` | Swift scrapers → `swift_export.json` |
| `collector/` | Python adapters (Swift export, boards, DOU careers) |
| `parser/` | Normalize, iOS filter, dedupe |
| `config/` | Project + Sync settings from env |
| `project_sync/` | Issues + Projects V2 GraphQL |
| `planner/` | Daily work from Project cards |
| `reporter/` | Hourly short alert + daily dashboard |
| `analytics/` | Pipeline summary helpers |
| `database/seen.py` | Dual-write seen store |
| `scripts/run_pipeline.py` | Collect → sync → hourly |
| `scripts/run_daily_report.py` | Planner → daily Telegram |
| `scripts/seed_project_from_seen.py` | Seed Archived from seen.json |

## Schedule

- **Collect:** every hour via `hourly-trigger.yml` → Collect
- **Daily report:** `daily-report.yml` (~04:00 UTC)
- **CI:** on push/PR to `main`
