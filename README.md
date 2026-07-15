# iOS Hunter

iOS Hunter is evolving into **Career Agent**: collect iOS/Swift vacancies, sync them to a GitHub Project board, and report ops status on Telegram.

Production runs on GitHub Actions. GitHub Project is the operational source of truth for vacancy status. Telegram gets a short hourly OK (and the vacancy list only when something new lands in Inbox).

See `docs/architecture/career-agent.md` and `docs/github-setup-guide.md`.

## What you get

**Telegram (every successful collect):**

```
📭 Новых вакансий не обнаружено

✅ Система работает · 2026-07-15 11:00
```

When there are **new** vacancies:

```
🆕 +2 Inbox

1. Senior iOS Engineer
   🏢 Acme
   📡 Ashby
   🔗 https://jobs.example.com/1

✅ Система работает · 2026-07-15 11:00
🔗 https://github.com/users/you/projects/1
```

**Pipeline status / Applied / Screening** — manage on the private [Career CRM Project](https://github.com/users/vil4max/projects/3). Telegram does **not** dump today's tasks or CRM sections.

DOU and Djinni board browsing stays in their native apps. This repo watches company career pages (and related DOU Top 50 career-site discovery).

## Secrets

| Secret | Required | Purpose |
|--------|----------|---------|
| `TELEGRAM_TOKEN` | yes | Bot API |
| `TELEGRAM_CHAT_ID` | yes | Your private chat |
| `CAREER_AGENT_TOKEN` | for Sync | Fine-grained PAT: Issues + Projects |

Remove unused repo secrets if present: `GEMINI_API_KEY`, `OPENAI_API_KEY`.

Repository variables:

| Variable | Purpose |
|----------|---------|
| `SEED_SEEN_ONLY` | `1` to mark/seed without hourly alert |
| `CAREER_AGENT_SYNC_ENABLED` | `1` to enable GitHub Project Sync |
| `CAREER_AGENT_SEEN_GATE` | `0` after cutover (default on) |
| `CAREER_PROJECT_OWNER` | User/org login owning the Project (`vil4max`) |
| `CAREER_PROJECT_NUMBER` | Project number from URL (`3`) |
| `PROJECT_BOARD_URL` | Link shown in Telegram |

## Pipeline

```
Swift collectors → swift_export.json
        ↓
Python sources (boards / DOU careers)
        ↓
Normalize + iOS/Swift filter → Deduplicate
        ↓
Project Sync (private Draft + Project Inbox) + seen.json dual-write
        ↓
Telegram only on new vacancies (list + OK)
```

## Workflows

| Workflow | When |
|----------|------|
| **Collect iOS Jobs** | Manual or via hourly trigger — collect, sync, Telegram if new |
| **Hourly Collect Trigger** | Every hour UTC — dispatches Collect on macOS |
| **Daily Career Report** | Manual only — Project plan counts to Actions log (no Telegram) |
| **CI** | Push / PR — Swift build + pytest |

## Local debug

```bash
swift build -c release
SWIFT_EXPORT_PATH=database/swift_export.json swift run -c release JobHunter
pip install -r requirements.txt
SEED_SEEN_ONLY=1 python3 scripts/run_pipeline.py
CAREER_AGENT_SYNC_ENABLED=1 python3 scripts/run_pipeline.py
python3 scripts/seed_project_from_seen.py --dry-run
python3 scripts/run_daily_report.py
```

Without Telegram secrets, messages print to stdout.

## Identity

Vacancies are keyed by canonical URL (tracking query params stripped). Project Sync is idempotent via `Canonical-URL` in the Issue body.
