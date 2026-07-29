# iOS Hunter

iOS Hunter is evolving into **Career Agent**: collect iOS/Swift vacancies, sync them to a GitHub Project board, and report ops status on Telegram.

Production runs on GitHub Actions. GitHub Project is the operational source of truth for vacancy status. Telegram gets a short OK during Kyiv business hours (09:00–18:00), and the vacancy list only when something new lands in Inbox.

See `docs/architecture/career-agent.md` and `docs/github-setup-guide.md`.

## What you get

**Telegram (every successful collect):**

```
📭 Новых вакансий не обнаружено

✅ Поиск по сайтам: OK (12/12)
✅ Telegram: OK (3/3)
📊 Найдено: 30 · в базе: 120 · новых: 0

✅ Все проверки прошли · 2026-07-15 11:00
```

When there are **new** vacancies:

```
🆕 +2 Inbox

1. Senior iOS Engineer
   📝 SwiftUI · remote
   🏢 Acme
   📡 Ashby
   🔗 https://jobs.example.com/1

✅ Поиск по сайтам: OK (12/12)
✅ Telegram: OK (3/3)
📊 Найдено: 32 · в базе: 120 · новых: 2

✅ Все проверки прошли · 2026-07-15 11:00
🔗 https://github.com/users/you/projects/1
```

**Pipeline status / Applied / Screening** — manage on the private [Career CRM Project](https://github.com/users/vil4max/projects/3). Telegram does **not** dump today's tasks or CRM sections.

DOU and Djinni board browsing stays in their native apps. This repo watches company career pages, the committed DOU company seed (`database/dou_companies.json`) plus DOU iOS/macOS RSS, and optional Telegram chats (`@itrecruit_ua`, `@remotejobss`, `@itfreelancers` — iOS/Swift hiring posts only).

Refresh the DOU company seed periodically (not on every pipeline run):

```bash
python3 scripts/discover_dou_companies.py
python3 scripts/discover_dou_companies.py --enrich-sites
python3 scripts/discover_dou_companies.py --max-pages 2 --limit 40 --dry-run
```

Daily collect only **reads** the seed. Active DOU company feeds are capped with `DOU_SEED_FEED_LIMIT` (default `300`; use `all` for no cap).

One-time Telegram chat setup:

```bash
pip install -r requirements.txt
python3 scripts/telegram_login.py
```

Then add `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_SESSION` as repository secrets. Your account must already be a member of the monitored chat.

## Secrets

| Secret | Required | Purpose |
|--------|----------|---------|
| `TELEGRAM_TOKEN` | yes | Bot API (outbound alerts) |
| `TELEGRAM_CHAT_ID` | yes | Your private chat |
| `TELEGRAM_API_ID` | for TG chats | MTProto app id from my.telegram.org |
| `TELEGRAM_API_HASH` | for TG chats | MTProto app hash |
| `TELEGRAM_SESSION` | for TG chats | StringSession from `scripts/telegram_login.py` |
| `CAREER_AGENT_TOKEN` | for Sync | Fine-grained PAT: Issues + Projects |
| `SMTP_USER` | for daily email + IMAP | Gmail address (e.g. `vil4max@gmail.com`) |
| `SMTP_PASS` | for daily email + IMAP | [Gmail App Password](https://myaccount.google.com/apppasswords) |
| `SMTP_FROM` | optional | From address (defaults to `SMTP_USER`) |

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
| `REPORT_EMAIL_TO` | Daily report recipient (default `vil4max@gmail.com`) |
| `SMTP_HOST` | optional SMTP host (default `smtp.gmail.com`) |
| `SMTP_PORT` | optional SMTP port (default `587`) |
| `IMAP_HOST` | optional IMAP host (default `imap.gmail.com`) |
| `IMAP_PORT` | optional IMAP port (default `993`) |
| `IMAP_FOLDER` | optional folder (default `INBOX`) |

## Pipeline

```
Python collectors (career pages / ATS / DOU / Telegram)
        ↓
Normalize + iOS/Swift filter + geo filter → Deduplicate
        ↓
Project Sync (private Draft + Project Inbox) + seen.json dual-write
        ↓
Telegram only on new vacancies (list + OK)
```

## Workflows

| Workflow | When |
|----------|------|
| **Collect iOS Jobs** | Manual or via hourly trigger — collect, sync, Telegram if new |
| **Hourly Collect Trigger** | Every hour at :17 UTC; dispatches Collect only Kyiv 09:00–18:00 |
| **Daily Vacancy Liveness** | Every day 04:00 UTC (incl. weekends) — probe active board URLs, archive closed, Telegram status |
| **Daily Email Report** | Every day 15:00 UTC (≈18:00 Kyiv) — full CRM + collect summary to email |
| **IMAP Recruiter Poll** | Every hour at :47 UTC (Kyiv 09:00–18:00) — classify recruiter mail, update CRM, Telegram |
| **CI** | Push / PR — pytest |

## Local debug

```bash
pip install -r requirements.txt
SEED_SEEN_ONLY=1 python3 scripts/run_pipeline.py
SEEN_PATH=/tmp/seen.json python3 scripts/run_pipeline.py
CAREER_AGENT_SYNC_ENABLED=1 python3 scripts/run_pipeline.py
python3 scripts/collector_parity.py
python3 scripts/seed_project_from_seen.py --dry-run
python3 scripts/run_vacancy_liveness.py --dry-run
python3 scripts/run_daily_report.py
python3 scripts/run_imap_poll.py --dry-run
```

Daily email needs `SMTP_USER` + `SMTP_PASS` (Gmail App Password) and Sync enabled. Without SMTP secrets the script exits with an error. Without Telegram secrets, Telegram messages print to stdout.

IMAP recruiter poll reuses the same `SMTP_USER` / `SMTP_PASS` App Password (`imap.gmail.com`). It updates matched Project cards (`Replied` / `Screening` / `Archived`+`Rejected HR`) and dedupes via `database/email_seen.json`.

## Identity

Vacancies are keyed by canonical URL (tracking query params stripped). Project Sync is idempotent via `Canonical-URL` in the Issue body.
