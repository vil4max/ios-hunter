# Career Agent Architecture

## Mission

Manage the job-search lifecycle: collect → Inbox → research/apply/interview → outcomes. GitHub Project is operational truth; Telegram is presentation.

## Layers

| Layer | Ownership |
|-------|-----------|
| Career Agent (this system) | Pipeline Status, daily plan, Telegram ops |
| Career Intelligence ([RFC](../../CAREER_PLATFORM_ARCHITECTURE.md)) | Scores, trends (later) |
| Personal Profile ledger | Private interview notes outside public Issues |

## Module map

```text
collector/          fetch RawJob (Swift CLI + Python adapters)
parser/             normalize, iOS filter, dedupe
config/             env: project, statuses, thresholds
project_sync/       Issues + Projects V2 GraphQL
planner/            read Project → prioritized work
reporter/           hourly short alert + daily dashboard
analytics/          pipeline counts for daily summary
scripts/            thin CLIs: run_pipeline, run_daily_report, seed_project
```

## Data flow

```text
Collect (hourly)
  → Filter → Deduplicator
  → Project Sync (create Issue+item Inbox if new URL)
  → dual-write seen.json
  → Telegram: Inbox +N (no vacancy list)

Daily report (~07:00 Europe/Kyiv)
  → GraphQL read Project
  → Planner
  → Reporter dashboard → Telegram
```

## Vacancy minimum model

Issue + Project fields: company, title, url, canonical_url, source, Status, Priority, Offer Probability (Low/Medium/High), Applied At, Follow Up, created/updated.

Manual / historical / collector vacancies use **private Draft Project items** (never public repo Issues) via Sync and `scripts/add_manual_card.py`.


## Status workflow

```text
Inbox
  ├─→ Applied → Screening → Technical → Offer
  │                              └────→ Rejected
  └─→ Archived   (not interested)
```

Columns (exact names): Inbox, Applied, Screening, Technical, Offer, Rejected, Archived.

## Boundaries

- Collector does not know Status.
- Planner does not scrape.
- Reporter does not call GitHub GraphQL (receives Planner DTOs / sync results).
