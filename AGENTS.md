# AGENTS.md

## Cursor Cloud specific instructions

This repo is a **Python** Career Agent pipeline ("iOS Hunter").
Standard commands live in `README.md` ("Local debug") and `CONTRIBUTING.md`
("Development"); this section only records non-obvious cloud caveats.

### Environment

- Dev runtime is **Python 3.12** (matches CI `python-check`).
- Dependencies are installed with `pip install --user` (see the startup update script).
  `apt` egress is blocked and `python3-venv`/`ensurepip` is unavailable, so a normal
  `python3 -m venv` fails; `pip install --user` is the working path. After the update
  script runs, invoke tools with plain `python3` (no venv activation needed).

### Python pipeline

- Test: `python3 -m pytest -q` (the suite makes **real network calls** to live job
  boards, so it takes ~75s; a fully offline run is not expected).
- Import check (mirrors CI): the one-liner in `CONTRIBUTING.md` / `ci.yml`.
- Run the app: `python3 scripts/run_pipeline.py`. It scrapes live company/DOU endpoints,
  normalizes + dedupes, and (without `TELEGRAM_*` secrets) **prints the alert to stdout**
  and reports `Sync skipped: True` (GitHub Project Sync stays off without
  `CAREER_AGENT_TOKEN` + `CAREER_AGENT_SYNC_ENABLED=1`).
- To avoid mutating the tracked `database/seen.json`, run with
  `SEEN_PATH=/tmp/seen.json python3 scripts/run_pipeline.py`.
- Collector coverage report: `python3 scripts/collector_parity.py`.
- Refresh DOU company catalog seed (periodic, not part of hourly collect):
  `python3 scripts/discover_dou_companies.py [--enrich-sites]`.
  Seed file: `database/dou_companies.json`. Collect reads it and adds DOU company
  feeds (active vacancies, capped by `DOU_SEED_FEED_LIMIT`, default 300).
