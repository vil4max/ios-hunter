# iOS Hunter

iOS Hunter monitors company career pages and sends newly discovered iOS / Swift vacancies to Telegram.

Production runs on GitHub Actions. Telegram is the only output channel.

## What you get

One Telegram message per collect run with all newly detected vacancies:

```
Вакансий 2 · 2026-07-10 11:47

1. Senior iOS Engineer
   Acme
   Ashby
   https://jobs.ashbyhq.com/acme/123

2. Swift Developer
   EPAM
   EPAM careers
   https://careers.epam.com/en/vacancy/ios-1
```

If there are no new vacancies, a short report is still sent:

```
Новых вакансий нет · 2026-07-10 18:00
Проверено: 21
```

Nothing else is sent. No match scores, cover letters, AI summaries, or market reports.

DOU and Djinni board browsing stays in their native apps. This repo watches company career pages (and related DOU Top 50 career-site discovery).

## Secrets

| Secret | Required | Purpose |
|--------|----------|---------|
| `TELEGRAM_TOKEN` | yes | Bot API |
| `TELEGRAM_CHAT_ID` | yes | Your private chat |

Remove unused repo secrets if present: `GEMINI_API_KEY`, `OPENAI_API_KEY`.

Optional repository variable for cutover:

| Variable | Purpose |
|----------|---------|
| `SEED_SEEN_ONLY` | Set to `1` for the first collect after deploy to mark all current vacancies as seen without Telegram. Clear it afterward. |

## Pipeline

```
Swift collectors → swift_export.json
        ↓
Python sources (boards / DOU careers)
        ↓
Normalize + iOS/Swift filter → Deduplicate
        ↓
Seen store (database/seen.json) → Telegram (new URLs, or empty report)
```

Seen state is committed to git after each collect so Actions cache loss cannot resend every vacancy.

## Workflows

| Workflow | When |
|----------|------|
| **Collect iOS Jobs** | Manual or via hourly trigger — collect and notify |
| **Hourly Collect Trigger** | Every hour UTC — dispatches Collect on macOS |
| **CI** | Push / PR — Swift build + pytest |

## Local debug

```bash
swift build -c release
SWIFT_EXPORT_PATH=database/swift_export.json swift run -c release JobHunter
pip install -r requirements.txt
SEED_SEEN_ONLY=1 python3 scripts/run_pipeline.py   # first run: seed only
python3 scripts/run_pipeline.py                    # notify new vacancies
```

Without Telegram secrets, messages print to stdout.

## Identity

Vacancies are keyed by canonical URL (tracking query params stripped). The same URL is never sent twice. Description changes and reopenings do not create another message.
