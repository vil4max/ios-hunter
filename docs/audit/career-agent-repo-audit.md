# Repository Audit — iOS Hunter (pre–Career Agent)

Audit date: 2026-07-15. Analysis only snapshot for Career Agent v1.

## Verdict

Reliable hourly vacancy notifier. Operational SoT is “URL already sent to Telegram” (`database/seen.json`). No application pipeline, Planner, or GitHub Project sync.

## Architecture (as implemented)

```text
hourly-trigger.yml → collect.yml (macOS)
  Swift JobHunter → database/swift_export.json
  Python run_pipeline.py
    collector (Swift export + ATS + DOU)
    normalize + iOS filter + dedupe
    seen.json gate → Telegram list or empty proof
    commit seen.json
```

## Modules

| Path | Role |
|------|------|
| `Sources/JobHunter/` | Swift collectors |
| `collector/` | Python adapters + DOU |
| `parser/` | Normalize, filter, dedupe |
| `database/seen.py` | Seen URL store |
| `integrations/` | Telegram |
| `scripts/run_pipeline.py` | Orchestrator |

Missing vs Career Agent: Project Sync, Planner, daily Reporter dashboard, Analytics, central Config.

## Vacancy persistence

`seen.json` keys = canonical URL; values = `{title, company, first_seen}` only. Descriptions and workflow status are discarded.

## Deduplication

Swift hash (company|title|location); Python identity (`source_job_id` / canonical URL / role collapse); seen gate by URL.

## GitHub

Actions hosting + seen commit only. No Projects / Issues vacancy board.

## Risks carried into Agent

Dual runtime source overlap; noisy iOS filter; seen ≠ pipeline state; dual-write drift until cutover.
