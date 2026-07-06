# iOS Hunter

Private personal job monitor. **Production runs on GitHub Actions only** — Telegram is the main output. Local clone is for config edits, CRM, and optional debugging.

Public profile for recruiters: [vil4max.github.io](https://vil4max.github.io). This repo is not published anywhere.

---

## Quick start (already set up)

| Secret | Required | Purpose |
|--------|----------|---------|
| `TELEGRAM_TOKEN` | yes | Bot API |
| `TELEGRAM_CHAT_ID` | yes | Your private chat |
| `GEMINI_API_KEY` | yes | Job Intelligence (fit, gaps, APPLY/CHECK/SKIP) |
| `OPENAI_API_KEY` | optional | Fallback LLM if you change `AI_PROVIDER` |

Repo: **private**. GitHub Pages: **off** (no public site/RSS).

Config you edit in git:

| File | What |
|------|------|
| `config/profile.yaml` | Name, links, skills, thresholds, Telegram toggle |
| `config/career_facts.yaml` | Grounded facts for Gemini (employers, projects) |
| `config/skills.yaml` | Skill aliases for matcher |
| `config/cover_letter_template.md` | Rules fallback only (when no LLM key) |

---

## Manual runs (GitHub)

**Actions** tab → pick workflow → **Run workflow** → branch `main` → **Run workflow**.

| Workflow | When to run manually |
|----------|-------------------|
| **Collect iOS Jobs** | Main run: collect, diff, Telegram, reports. Use after config changes or when you want a fresh scan outside the schedule. |
| **Weekly iOS Market Report** | Regenerate `reports/weekly/` if the DB cache exists but Monday cron missed. |
| **AI Analysis** | Append AI text to weekly report (needs `GEMINI_API_KEY` or `OPENAI_API_KEY`). |
| **CI** | Runs on push/PR automatically — Swift build + pytest. |

After **Collect**, check:

1. Workflow log — `Application packs sent: N`
2. Telegram — actionable jobs (new / updated / reopened)
3. `reports/activity/latest.md` in repo — last run summary

### Automatic schedule (Europe/Kyiv)

Cron is UTC in workflow files; local times below are **summer (EEST, UTC+3)**. In winter (EET) add **+1 hour**.

| Workflow | Local time | UTC cron |
|----------|------------|----------|
| Collect | Sun 18:00–21:00, Mon–Fri 08:00–18:00 (hourly) | `0 15-18 * * 0`, `0 5-15 * * 1-5` |
| Weekly report | Mon 09:00 | `0 6 * * 1` |
| AI summary | Mon 12:30 | `30 9 * * 1` |

---

## What you get in Telegram

**Actionable event** = job is new, updated, or reopened.

| Path | When | Message |
|------|------|---------|
| **Gemini** (`GEMINI_API_KEY` set) | prefilter ≥ 45, notify if fit ≥ 60 and priority medium/high | Compact intelligence: score, gaps, recommendation, links. No cover letter. |
| **Rules fallback** (no LLM key) | match ≥ 60 | Older format with cover letter draft. |

Also: **Company Watch** (3+ iOS/mobile roles at one company, max once/week) and **CRM follow-ups** (if configured in pipeline).

DOU / Djinni are **not** scraped — use their apps.

---

## Data & storage

```
Swift collector → swift_export.json
       ↓
Python pipeline → jobs.db (SQLite)
       ↓
Telegram + reports/*.md (committed to private main)
```

| Data | Where | In git? |
|------|-------|---------|
| Job history, descriptions, analysis cache | `database/jobs.db` | **No** — GHA cache key `ios-hunter-db-<repo>` |
| Run reports | `reports/` | Yes (private repo only) |
| Profile / career facts | `config/` | Yes (private repo only) |

Retention: jobs not seen for **45 days** are pruned (`JOBS_RETENTION_DAYS` env).

**Important:** If cache is lost (repo rename, cache expiry, long idle), the next collect treats vacancies as **new** — possible duplicate Telegram alerts until state rebuilds.

---

## Local clone (optional)

Production DB lives in **Actions cache**, not in the clone. Local run starts with an empty or stale `database/jobs.db` unless you copy a DB file yourself.

```bash
# macOS — full pipeline (same as CI collect job)
swift build -c release
SWIFT_EXPORT_PATH=database/swift_export.json swift run -c release JobHunter
pip install -r requirements.txt
export TELEGRAM_TOKEN=... TELEGRAM_CHAT_ID=... GEMINI_API_KEY=...
export JOBS_DB_PATH=database/jobs.db
python3 scripts/run_pipeline.py
```

```bash
# Tests
pip install -r requirements.txt -r requirements-dev.txt
python3 -m pytest -q
```

**CRM** (needs local `jobs.db` with application data):

```bash
python3 -m crm apply --company "Acme" --title "Senior iOS"
python3 -m crm list
python3 -m crm stage --id 1 --stage hr_screen
python3 -m crm stats
python3 -m crm remind   # needs TELEGRAM_* env
```

---

## Git push from your machine

Workflow file changes require a token/remote with **`workflow` scope`. OAuth without it rejects pushes that touch `.github/workflows/*`.

Use SSH, GitHub Desktop, or `gh auth login` with workflow permission.

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| No Telegram | Secrets; `config/profile.yaml` → `telegram.enabled: true`; workflow log for errors |
| No LLM block in message | `GEMINI_API_KEY` in secrets; collect workflow sets `AI_PROVIDER=gemini` |
| Duplicate “new” alerts | Cache miss — normal after first run on fresh cache |
| Collect fails on Swift | `reports/health/latest.md`; source may be down or HTML changed |
| Push rejected (workflow scope) | Re-auth with workflow scope or use SSH |

---

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — modules and pipeline steps
- [ROADMAP.md](ROADMAP.md) — feature backlog
