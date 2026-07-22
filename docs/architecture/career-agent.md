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
  → Project Sync (private Draft Inbox if new URL)
  → dual-write seen.json
  → Telegram each run: datetime · OK · (новых нет | list)

Ops status / Applied → Screening: GitHub Project board (no daily Telegram CRM dump)
```

## Vacancy minimum model

Issue + Project fields: company, title, url, canonical_url, source, Status, Priority, Offer Probability (Low/Medium/High), Applied At, Follow Up, created/updated.

Manual / historical / collector vacancies use **private Draft Project items** (never public repo Issues) via Sync and `scripts/add_manual_card.py`.


## Status workflow

```text
Inbox
  └─→ Applied → Replied → Screening → Post-Screen → Technical → Post-Tech
                                                                      └─→ Archived
```

Columns (exact names): Inbox, Applied, Replied, Screening, Post-Screen, Technical, Post-Tech, Archived.

Terminal outcomes are not Status columns. Always archive with Close Reason + Closed Stage:
- no reply after wait window → `No reply`
- HR/recruiter reject → `Rejected HR`
- tech reject → `Rejected tech`
- offer → `Accepted offer` / `Declined offer` (Closed Stage `Offer`)
- other → `Duplicate` / `Withdrawn` / …

## Boundaries

- Collector does not know Status.
- Planner does not scrape.
- Reporter does not call GitHub GraphQL (receives Planner DTOs / sync results).
