# AGENTS.md

## Cursor Cloud specific instructions

This repo is a hybrid **Python pipeline + Swift collector** ("iOS Hunter" / Career Agent).
On the Linux cloud VM, only the **Python** side is runnable and testable; the Swift side
is macOS-only (see below). Standard commands live in `README.md` ("Local debug") and
`CONTRIBUTING.md` ("Development"); this section only records non-obvious cloud caveats.

### Environment

- Dev runtime is **Python 3.12** (matches CI `python-check`). The runnable app + tests
  are Python-only on this VM.
- Dependencies are installed with `pip install --user` (see the startup update script).
  `apt` egress is blocked and `python3-venv`/`ensurepip` is unavailable, so a normal
  `python3 -m venv` fails; `pip install --user` is the working path. After the update
  script runs, invoke tools with plain `python3` (no venv activation needed).

### Python pipeline (primary, runnable here)

- Test: `python3 -m pytest -q` (the suite makes **real network calls** to live job
  boards, so it takes ~75s; a fully offline run is not expected).
- Import check (mirrors CI): the one-liner in `CONTRIBUTING.md` / `ci.yml`.
- Run the app: `python3 scripts/run_pipeline.py`. It scrapes live company/DOU endpoints,
  normalizes + dedupes, and (without `TELEGRAM_*` secrets) **prints the alert to stdout**
  and reports `Sync skipped: True` (GitHub Project Sync stays off without
  `CAREER_AGENT_TOKEN` + `CAREER_AGENT_SYNC_ENABLED=1`).
- To avoid mutating the tracked `database/seen.json`, run with
  `SEEN_PATH=/tmp/seen.json python3 scripts/run_pipeline.py`.

### Swift collector (macOS-only — NOT buildable on this VM)

- `Sources/JobHunter/` builds via `swift build -c release` / `swift run -c release JobHunter`,
  but `Package.swift` declares `.macOS(.v13)` and CI builds it on `macos-latest`. The Swift
  toolchain is not installed on the Linux cloud VM and cannot be added (apt egress blocked),
  so `swift build`/`swift run` cannot be exercised here.
- Its output `database/swift_export.json` is an **optional** input: the Python collector
  (`collector.companies.load_swift_export`) returns an empty list when the file is missing,
  so the pipeline runs fine without it.
