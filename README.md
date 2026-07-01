# ios-hunter

iOS Hunter monitors the Ukrainian iOS job market and accelerates your response to actionable vacancies.

## What it does

1. **Collects** iOS/Swift vacancies from company career pages (Swift collector, 52 sources)
2. **Detects changes** — New, Updated, Closed, Reopened
3. **First-to-apply** — match score, cover letter, CV/portfolio links via Telegram
4. **Tracks health** — per-source failures with HTTP codes and consecutive failure counts

## Salary filter

Configured in [`config/profile.yaml`](config/profile.yaml):

- Range: **$4500–$6000** net (current English B1)
- Below **$4500** detected salary → filtered out from application packs
- With English 7–8 (B2–C1): raise to **$7000–$8000** in `config/profile.yaml`

## Stack

Swift 6 (collector) · Python 3.12 (pipeline) · SQLite · GitHub Actions (hourly) · Telegram

## Run locally

```bash
# Swift collector
swift run -c release JobHunter

# Python pipeline
pip install -r requirements.txt
python scripts/run_pipeline.py
```

## Environment

| Variable | Description |
|----------|-------------|
| `TELEGRAM_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Chat ID for notifications |
| `JOBS_DB_PATH` | Python SQLite path (default: `database/jobs.db`) |
| `SWIFT_EXPORT_PATH` | Swift JSON export (default: `database/swift_export.json`) |

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
