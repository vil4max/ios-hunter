# iOS Hunter Architecture

## Overview

```
GitHub Actions (hourly)
        │
   Swift Collector (52 company sources)
        │ swift_export.json
   Python Pipeline
        │
   ┌────┴────┬──────────┬────────────┐
   │         │          │            │
 SQLite   Activity   Health    Application Pack
   │         │          │            │
 Reports  Markdown   Markdown    Telegram
   │
 GitHub Pages (public analytics)
```

## Pipeline

1. Swift collector fetches iOS vacancies from company career pages
2. Export all open jobs to `database/swift_export.json`
3. Python normalizes, deduplicates, diffs, and detects actionable events
4. For actionable jobs above match threshold: build cover letter + CV links
5. Send Telegram application pack
6. Write Run Activity + Collector Health reports

## Modules

| Module | Role |
|--------|------|
| `collector/` | Download vacancies (Swift export + Python adapters) |
| `parser/` | Normalize, dedup, diff, activity summary |
| `apply/` | Match score, cover letter, resume picker, application pack |
| `database/` | SQLite schema and repository |
| `integrations/` | Telegram notifications |
| `crm/` | Application tracking (Phase 2) |
| `statistics/` | Market intelligence (Phase 3) |

## Design Principles

- Zero-cost hosting (GitHub + GitHub Pages)
- No backend server
- GitHub Actions only
- SQLite as primary database
- AI optional (rules-based matching first)
- Salary range: $4500–$6000 net (B1); aspirational $7000–$8000 with English 7–8
