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

Quick checklist:

1. **Merge PR** into `main`
2. **Secrets** (Settings → Secrets and variables → Actions):
   - `TELEGRAM_TOKEN` — from [@BotFather](https://t.me/BotFather)
   - `TELEGRAM_CHAT_ID` — your Telegram chat id
3. **Enable Actions** — repo → Actions tab
4. **GitHub Pages** — Settings → Pages → Source: **GitHub Actions**
5. Edit **`config/profile.yaml`** — your name, portfolio, CV URLs

After setup, `collect.yml` runs hourly, sends Telegram packs, and **auto-commits** reports to `main`.

## Docs

- [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md) — подробная настройка GitHub
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
