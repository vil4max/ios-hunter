# ios-hunter

iOS Hunter monitors the Ukrainian iOS job market and accelerates your response to actionable vacancies.

## What it does

1. **Collects** iOS/Swift vacancies from company career pages (Swift, ~52 sources)
2. **Detects changes** — New, Updated, Closed, Reopened
3. **First-to-apply** — match score, cover letter, CV/portfolio links via Telegram
4. **Tracks health** — per-source failures with HTTP codes

DOU and Djinni are **not** collected here — track them in your iPhone apps.

## Salary filter

Configured in [`config/profile.yaml`](config/profile.yaml):

- Range: **$4500–$6000** net (current English B1)
- Below **$4500** detected salary → filtered out from application packs
- With English 7–8 (B2–C1): raise to **$7000–$8000** in `config/profile.yaml`

## Stack

Swift 6 (collector) · Python 3.12 (pipeline) · SQLite (`database/jobs.db`) · GitHub Actions · Telegram

## Run locally

```bash
# 1. Swift collector → database/swift_export.json
swift run -c release JobHunter

# 2. Python pipeline → database/jobs.db + reports + Telegram
pip install -r requirements.txt
python3 scripts/run_pipeline.py

# Weekly report only (from existing DB)
python3 scripts/weekly_report.py
```

## Environment

| Variable | Description |
|----------|-------------|
| `TELEGRAM_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Chat ID for notifications |
| `JOBS_DB_PATH` | SQLite path (default: `database/jobs.db`) |
| `SWIFT_EXPORT_PATH` | Swift JSON export (default: `database/swift_export.json`) |
| `OPENAI_API_KEY` | Optional — enable AI weekly summary |
| `GEMINI_API_KEY` | Optional — enable AI weekly summary (fallback) |

## Schedule (GitHub Actions)

| Workflow | When |
|----------|------|
| Collect iOS Jobs | Every hour, **Mon–Fri 08:00–18:00 Kyiv** |
| Weekly iOS Market Report | Monday 09:00 Kyiv |
| AI Analysis | Monday 09:30 Kyiv (optional, off without API key) |

## CRM

```bash
python3 -m crm apply --company MacPaw --title "Senior iOS Engineer" --source company
python3 -m crm list
python3 -m crm followups
python3 -m crm remind
python3 -m crm stats
python3 -m crm stage --id 1 --stage technical
```

## GitHub setup

One-time setup after merging the PR. Full guide (RU): **[docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md)**

## Docs

- [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md) — настройка GitHub
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
