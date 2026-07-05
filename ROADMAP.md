# iOS Hunter Roadmap

## Goal

Remote iOS role with an international team (current English B1). Raise target level when English reaches 7–8 (B2–C1).

## Priority Stack

### P1 — First-to-apply

- [x] Python pipeline with actionable events (New/Updated/Closed/Reopened)
- [x] Rules-based match score (threshold-based)
- [x] Template cover letter + resume version picker
- [x] Telegram application pack
- [x] Hourly weekday collect (08:00–18:00 Kyiv)
- [x] Company Watch (3+ mobile roles alert)
- [x] Description fetch for better matching (limited per run)

### P2 — Recruiter CRM

- [x] `applications` CLI (`python -m crm apply/list/stage/stats`)
- [x] Follow-up reminders via Telegram (`python -m crm remind`)
- [x] Conversion stats by source and resume version
- [ ] Interview notes CLI

### P3 — Market intelligence (private)

- [x] Weekly iOS Market Report (`reports/weekly/`)
- [x] Market Timeline snapshots (`reports/timeline/`)
- [x] Auto-commit reports after each run (private repo)
- [x] ~~GitHub Pages dashboard~~ — removed (Telegram-only)
- [x] ~~RSS feed~~ — removed

### P4 — AI (optional)

- [x] AI provider abstraction (`ai/engine.py`) — NoOp by default
- [x] Optional OpenAI / Gemini weekly summary (`ai-analysis.yml`)
- [ ] Semantic match score with OpenAI/Gemini API key
- [ ] Personalized cover letters
- [ ] Resume gap analysis

## Future Ideas

- Recruiter Watch
- Interview Knowledge Base
- DOU / Djinni — tracked manually via iPhone apps (not collected here)
- [ ] LinkedIn collector (stub — deferred)
- [ ] Full Python port of 52 Swift scrapers
