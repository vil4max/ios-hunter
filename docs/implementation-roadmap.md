# Implementation Roadmap — Career Agent v1

## Phase 0 — Docs (done in repo)

ADR, audit, architecture, GitHub setup guide, migration plan, this roadmap.

## Phase 1 — Config + Project Sync

- `config/settings.py`
- `project_sync/` GraphQL client + sync
- Mocked unit tests

## Phase 2 — Wire collect

- `scripts/run_pipeline.py` calls Sync after dedupe
- Short hourly Telegram
- Dual-write `seen.json`
- `collect.yml` secrets/vars
- `scripts/seed_project_from_seen.py`

## Phase 3 — Planner + daily Reporter

- `planner/plan.py`
- `reporter/` hourly + daily
- `scripts/run_daily_report.py`
- `.github/workflows/daily-report.yml`

## Phase 4 — Hygiene

Keep dual collectors; clarify package boundaries without big rewrites.

## Phase 5 — Cutover

After Sync stability: stop using `seen.json` as notify gate. See [migration-plan.md](migration-plan.md).

## Non-goals (this wave)

Intelligence scores, company registry rewrite, Djinni, web UI, deleting Swift scrapers.
