# iOS Hunter

iOS Hunter is a private **company-career radar** inside the wider Career Evolution System. Its bounded responsibility is to monitor official career pages and ATS endpoints of large Ukrainian service companies for iOS/Swift vacancies, synchronize operational data with the Career CRM Project, and report collection status. Career direction, competency development, interview knowledge, English progress, and canonical career facts belong to their owning workspaces — not here.

Production runs on GitHub Actions. GitHub Project is the operational source of truth for vacancy status. Telegram gets a short OK on the Kyiv collect slots (09:00 / 12:00 / 15:00 / 18:00), and the vacancy list only when something new lands in Inbox. Live ops channels are Telegram, the daily email (after the Kyiv 18:00 collect), and the Project board — `reports/*.md` are static audit notes, not runtime dashboards.

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

DOU and Djinni vacancy browsing stays in their native apps and is not part of production collection. This repo watches official company career pages and ATS endpoints. Optional Telegram chats (`@itrecruit_ua`, `@remotejobss`, `@itfreelancers`, `@mobile_jobs`) remain a supplementary channel and do not count as company coverage.

Refresh the DOU service-company watchlist periodically. `--resolve-careers` applies the committed official-URL overrides after discovery, so validated URLs are not lost on refresh:

```bash
python3 scripts/refresh_dou_service_watchlist.py
python3 scripts/refresh_dou_service_watchlist.py --resolve-careers
python3 scripts/refresh_dou_service_watchlist.py --dry-run
python3 scripts/discover_dou_companies.py
python3 scripts/discover_dou_companies.py --enrich-sites
python3 scripts/discover_dou_companies.py --max-pages 2 --limit 40 --dry-run
```

Daily collection does not read DOU vacancy feeds or Djinni.

The watchlist combines DOU service-rating companies with DOU Top 50 companies that have a verified official career URL. DOU rating metadata is intentionally limited to the overall score, compensation score, and survey count. Every watchlist company has a registered production source; companies with custom API collectors use them, and the rest use the generic official-page monitor.

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
| `SMTP_PASS` | for daily email + IMAP | [Gmail App Password](https://myaccount.google.com/apppasswords) (16 chars; spaces ok) |
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
| `IMAP_FOLDER` | Mailbox to poll (default `[Gmail]/All Mail` — includes Archive; use `INBOX` for inbox-only) |

## Pipeline

```
Official company collectors (career pages / ATS) + optional Telegram
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
| **Collect iOS Jobs** | Manual or via schedule trigger — collect, sync, Telegram; after Kyiv 18:00 slot also dispatches Daily Email |
| **Collect Schedule Trigger** | Hourly :17 UTC in daytime band; Kyiv due-slot 09/12/15/18 with catch-up + slot dedupe; Collect only |
| **Daily Vacancy Liveness** | Every day 04:00 UTC (incl. weekends) — probe active board URLs, archive closed, Telegram status |
| **Daily Email Report** | Kyiv 18:00 via Collect and/or schedule trigger (even if Collect already ran/failed) — claim day on `main` before SMTP; manual `force` re-sends |
| **IMAP Recruiter Poll** | After Collect completes (`workflow_run`) or manual — classify recruiter mail, update CRM, Telegram |
| **CI** | Push / PR — pytest |

## Local Collect kick (GHA lag kludge)

If GitHub Actions `schedule` is late and a Kyiv slot (09/12/15/18) is still unmarked after 15 minutes, a Mac launchd agent can dispatch **Collect iOS Jobs** via `gh`. This is a backup nudge only — not a replacement for remote cron, and it does not run the pipeline locally. IMAP still follows Collect via `workflow_run`.

Requires Mac timezone `Europe/Kyiv`, `gh` auth, and a clean fetch of `origin/main`.

```bash
chmod +x scripts/kick_collect_if_due.sh scripts/install_collect_kick_launchd.sh
./scripts/install_collect_kick_launchd.sh install   # 09:15 / 12:15 / 15:15 / 18:15 local
./scripts/install_collect_kick_launchd.sh status
./scripts/install_collect_kick_launchd.sh uninstall
./scripts/kick_collect_if_due.sh                    # manual dry check + maybe dispatch
```

Log: `~/Library/Logs/ios-hunter-collect-kick.log`

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
python3 scripts/run_hirify_sync.py --dry-run
python3 scripts/run_hirify_sync.py --xlsx ~/Downloads/my_applications_2026-07-29.xlsx
python3 scripts/should_kick_collect.py
```

Daily email needs `SMTP_USER` + `SMTP_PASS` (Gmail App Password) and Sync enabled. Without SMTP secrets the script exits with an error. Without Telegram secrets, Telegram messages print to stdout.

IMAP recruiter poll reuses the same `SMTP_USER` / `SMTP_PASS` App Password (`imap.gmail.com`).
Default folder is `[Gmail]/All Mail` so archived Spark/Gmail mail is included.
It updates matched Project cards (`Replied` / `Screening` / `Archived`+`Rejected HR`) and dedupes via `database/email_seen.json`.
If the workflow fails with `AUTHENTICATIONFAILED` / Invalid credentials, regenerate the App Password and update `SMTP_PASS` (IMAP access must stay enabled in Gmail settings).

Hirify Applications sync is local-first: export Excel from https://hirify.me/applications, then run `scripts/run_hirify_sync.py` (defaults to latest `~/Downloads/my_applications_*.xlsx`). Stages map into CRM with no-downgrade; fingerprints live in `database/hirify_seen.json`.

## Identity

Vacancies are keyed by canonical URL (tracking query params stripped). Project Sync is idempotent via `Canonical-URL` in the Issue body.
