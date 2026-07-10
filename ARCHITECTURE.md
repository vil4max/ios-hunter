# iOS Hunter Architecture

## Overview

```
GitHub Actions (hourly)
        │
   Swift Collector (company career pages)
        │ database/swift_export.json
   Python Pipeline
        │
   Normalize → Deduplicate → Seen store → Telegram
```

## Pipeline

1. Swift scrapers fetch iOS / Swift vacancies from company career pages and write `database/swift_export.json`.
2. Python loads the Swift export plus additional Python sources (job boards, DOU Top 50 career-site discovery).
3. Vacancies are normalized and filtered to iOS / Swift titles (or descriptions).
4. In-run deduplication collapses identical identity keys and same company+title roles.
5. Each vacancy’s canonical URL is checked against `database/seen.json`.
6. Unseen vacancies are sent in one Telegram message (`title`, `company`, `source`, `url`), then recorded in the seen store. If none are new, a short “no new vacancies” report is sent (checked count + Kyiv timestamp). Seed-only runs send nothing.
7. Collect workflow commits `database/seen.json` when it changes (`[skip ci]`).

## State

**`database/seen.json`** is the durable seen-vacancy store (committed to git).

```json
{
  "https://example.com/jobs/123": {
    "title": "Senior iOS Engineer",
    "company": "Acme",
    "first_seen": "2026-07-10T10:00:00+00:00"
  }
}
```

There is no SQLite database. Identity is the canonical vacancy URL.

Bootstrap options:

- Migrate URLs from a leftover `database/jobs.db` on first empty seen load.
- Or run with `SEED_SEEN_ONLY=1` / `--seed-only` to mark the current market as seen without Telegram.

## Modules

| Module | Role |
|--------|------|
| `Sources/JobHunter/` | Swift scrapers → `swift_export.json` |
| `collector/` | Python adapters (Swift export, boards, DOU careers) |
| `parser/` | Normalize, iOS filter, dedupe |
| `database/seen.py` | Load / save / migrate seen store |
| `integrations/` | Telegram send + message format |
| `scripts/run_pipeline.py` | Collect → notify new vacancies |

## Design principles

- Zero-cost hosting (GitHub Actions + private repo)
- No backend server, no LLM
- Telegram as the only output channel
- Minimal durable state: have I already sent this URL?
- Hourly trigger on ubuntu dispatches macOS Collect (macOS cron is unreliable)

## Schedule

- **Collect:** every hour via `hourly-trigger.yml` → `workflow_dispatch` of Collect
- **CI:** on push/PR to `main`
