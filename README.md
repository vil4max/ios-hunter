# iOS Hunter

An iOS/Swift vacancy monitor for the Ukrainian market. It runs **only on GitHub Actions** — no local setup required.

On weekdays, the bot scans company career pages, detects changes, and sends **new/updated/reopened vacancies** to Telegram when they match your profile.

DOU and Djinni are intentionally **not collected** — use their native apps instead.

---

## What it does

### 1. Collect vacancies
- **~52 company career pages** (Swift collector)
- Plus Teamtailor JSON feeds (Levi9, Avenga)
- Title filter: iOS / Swift

### 2. Track changes
Each vacancy has a history. On each run we detect:

| Event | Meaning |
|---------|------------|
| **New** | Appeared for the first time |
| **Updated** | Title or description changed |
| **Reopened** | A previously closed job is open again |
| **Closed** | No longer present on the website |

### 3. Telegram notifications
For **actionable** events (New / Updated / Reopened) with match score ≥ 60 you receive an **application pack**:

- company, title, link
- match score, Strong / Gap
- cover letter draft
- portfolio and CV links

There is no salary-based filtering in the public pipeline.

### 4. Company Watch
If a company has **3+ open mobile/iOS roles**, you get a separate Telegram alert (max once per week per company).

### 5. Reports and public artifacts
After each run, the repository is updated with:

- `reports/activity/` — per-run activity
- `reports/health/` — source health
- `reports/market/`, `reports/timeline/` — market snapshot
- `reports/weekly/` — weekly report
- `website/` — dashboard and RSS (GitHub Pages)

The SQLite DB (`database/jobs.db`) is stored in GitHub Actions cache and **not committed**.
To keep the cache bounded, the pipeline prunes jobs not seen for **45 days** (configurable via `JOBS_RETENTION_DAYS`).

### 6. CRM (optional)
Track applications and follow-up reminders via CLI (optional).

---

## Schedule (GitHub Actions)

| Workflow | When |
|----------|-------|
| **Collect iOS Jobs** | Sun **18:00–21:00** + Mon–Fri **08:00–18:00** Kyiv (hourly) |
| **Weekly iOS Market Report** | Monday 09:00 Kyiv |
| **AI Analysis** | Monday 09:30 (only if `OPENAI_API_KEY` or `GEMINI_API_KEY` is set) |

Manual run: **Actions → Collect iOS Jobs → Run workflow**.

---

## How it works

```
GitHub Actions (macOS + Ubuntu)
        │
   Swift — collects jobs from career pages
        │ swift_export.json
   Python — dedupe, diff, database, Telegram, reports
        │
   database/jobs.db (cache)  →  Telegram
        │
   auto-commit reports + website → main
```

Stack: Swift 6 · Python 3.12 · SQLite · Telegram Bot API · GitHub Pages

---

## Setup (one-time)

1. Add secrets: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
2. Enable GitHub Actions + GitHub Pages
3. Edit `config/profile.yaml` (name, portfolio, CV links)

---

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — architecture
- [ROADMAP.md](ROADMAP.md) — roadmap
