# GitHub Setup Guide — Career Agent (exact)

Architecture is finalized (ADR 0001). Target project: [Career CRM](https://github.com/users/vil4max/projects/3) (`vil4max` / `#3`).

Automate with: `python3 scripts/setup_github_project.py` (fields + Status).  
Repo wiring: `gh` label / variables / secrets (done in setup session 2026-07-15).

## Done via API (2026-07-15)

| Item | Status |
|------|--------|
| Status options Inbox … Archived | Done |
| Fields URL, Company, Source, Canonical URL, Applied At, Follow Up, Priority, Offer Probability | Done |
| Label `vacancy` | Done |
| Vars `CAREER_PROJECT_OWNER`, `CAREER_PROJECT_NUMBER`, `PROJECT_BOARD_URL`, `CAREER_AGENT_SYNC_ENABLED` | Done |
| Secret `CAREER_AGENT_TOKEN` (from current `gh` OAuth token) | Done |
| Deleted unused `GEMINI_API_KEY` | Done |
| Repo linked: `vil4max/ios-hunter` | Already linked |

Note: Actions forbids custom vars named `GITHUB_*`. Code reads `CAREER_PROJECT_OWNER` / `CAREER_PROJECT_NUMBER` (legacy `GITHUB_PROJECT_*` still works locally).

## Still manual / optional

### 1. Board view (UI only)

1. Open https://github.com/users/vil4max/projects/3  
2. Ensure a **Board** view grouped by **Status** with columns Inbox → … → Archived.

### 2. Make repository private (recommended)

Repo is still **public** — vacancy Issues would be public.

1. https://github.com/vil4max/ios-hunter/settings  
2. Danger Zone → Change visibility → **Private**

Or ask the agent to run: `gh repo edit vil4max/ios-hunter --visibility private`

### 3. Prefer fine-grained PAT (optional hardening)

`CAREER_AGENT_TOKEN` currently stores the CLI OAuth token (`project` + `repo`). Longer-term:

1. Create fine-grained PAT: Issues R/W on `ios-hunter` + Projects R/W  
2. `gh secret set CAREER_AGENT_TOKEN --repo vil4max/ios-hunter`

### 4. Seed Archived from `seen.json`

```bash
export CAREER_AGENT_TOKEN="$(gh auth token)"
export GITHUB_REPOSITORY=vil4max/ios-hunter
export CAREER_PROJECT_OWNER=vil4max
export CAREER_PROJECT_NUMBER=3
export CAREER_AGENT_SYNC_ENABLED=1
python3 scripts/seed_project_from_seen.py --dry-run
python3 scripts/seed_project_from_seen.py
```

### 5. Verify Collect + Daily

1. Actions → Collect iOS Jobs → Run  
2. Confirm Inbox Issue + Telegram `Inbox +N`  
3. Actions → Daily Career Report → Run  

### 6. Cutover later

After 3–7 stable days: set var `CAREER_AGENT_SEEN_GATE=0`  
See `docs/migration-plan.md`.

## Exact values (locked)

| Knob | Value |
|------|-------|
| Project URL | https://github.com/users/vil4max/projects/3 |
| Project node id | `PVT_kwHOABVlTc4Bdb8R` |
| Owner | `vil4max` |
| Number | `3` |
| Repository | `vil4max/ios-hunter` |

## Status names (exact)

Inbox, Applied, Screening, Technical, Offer, Rejected, Archived

Flow: new → Inbox → Applied (or Archive) → Screening → Technical → Offer | Rejected.

## Do not configure

- Second Project  
- Webhooks (v1 is pull-based)  
- Extra Status names / Intelligence score fields  
