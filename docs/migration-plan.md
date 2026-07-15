# Migration Plan — seen.json → GitHub Project

## Goal

Move operational truth from `database/seen.json` (notified URLs) to GitHub Project Status without Telegram floods or lost history.

## Phases

### M1 — Dual-write (current Agent v1)

1. Collect, filter, dedupe as today.
2. For URLs not in `seen.json`, Project Sync creates Issue + Project item (Status Inbox).
3. Mark URL in `seen.json` after successful Sync (and hourly alert).
4. Hourly Telegram: short Inbox +N only.

### M2 — Seed legacy seen

1. Run `python3 scripts/seed_project_from_seen.py` with Sync enabled.
2. Each `seen.json` URL becomes Issue + item with Status **Archived** (no Telegram).
3. Existing entries remain in `seen.json`.

### M3 — Daily dashboard live

Enable `daily-report.yml`. Planner reads Project only.

### M4 — Cutover (after 3–7 stable days)

1. Set `CAREER_AGENT_SEEN_GATE=0` (or remove seen gate in code after approval).
2. Sync idempotency (Canonical-URL) becomes the only “already known” check for Telegram.
3. Optionally archive `seen.json` commits; keep file as sync journal or delete in a later chore.

## Rollback

- Disable `CAREER_AGENT_SYNC_ENABLED`.
- Restore listing notify from git history if needed.
- `seen.json` continues to work as before for gate behaviour when Sync is off.

## Cutover checklist

- [ ] Project statuses and fields match setup guide
- [ ] Seed Archived completed (`python3 scripts/seed_project_from_seen.py`)
- [ ] Collect creates Inbox items for new vacancies only
- [ ] Hourly short alerts match Sync created count
- [ ] Daily report sections render with real Project data
- [ ] No duplicate Issues for same Canonical-URL
- [ ] Set repository variable `CAREER_AGENT_SEEN_GATE=0` (or unset gate in a follow-up) only after the above
- [ ] Optionally stop committing `seen.json` once Sync-only identity is trusted

## Code hooks for cutover

| Knob | Default | Cutover value |
|------|---------|---------------|
| `CAREER_AGENT_SYNC_ENABLED` | off | `1` |
| `CAREER_AGENT_SEEN_GATE` | on (`true`) | `0` after 3–7 stable days |

When `CAREER_AGENT_SEEN_GATE=0`, collect treats Sync idempotency as the primary “already known” check for every vacancy in the run (fresh = all normalized jobs; Sync skips existing Canonical-URLs). Keep dual-write of successful syncs to `seen.json` until you deliberately stop committing it.