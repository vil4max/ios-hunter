# ADR 0001 — Career Agent Architecture

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-07-15 |
| Context | iOS Hunter → Career Agent |

## Context

iOS Hunter collects vacancies and notifies Telegram when a canonical URL is new relative to `database/seen.json`. That is insufficient for a full job-search lifecycle (research, apply, interviews, follow-ups, metrics).

Career Agent must manage pipeline state with GitHub as source of truth, GitHub Project as the operational board, and Telegram as the daily interface.

## Decision

1. **Modular pipeline** with single-responsibility packages: Collector (existing Swift/Python), Filter, Deduplicator, Project Sync, Planner, Reporter, Analytics, Configuration.
2. **Operational source of truth** is GitHub Projects V2: **private Draft items** (not public repo Issues), Status single-select for workflow columns, custom fields for URL/company/source/dates/priority/offer probability.
3. **Sync stack** is Projects V2 GraphQL (`addProjectV2DraftIssue`, `updateProjectV2ItemFieldValue`). Public Issues are forbidden for vacancy CRM in a public repo.
4. **Telegram**: notify only on new Inbox vacancies (datetime · OK · list). Pipeline CRM stays on the Project board — no daily Telegram dashboard.
5. **`seen.json` dual-write** during migration; Sync idempotency is primary. Cut over after Sync stability.
6. **Career Intelligence Platform** ([`CAREER_PLATFORM_ARCHITECTURE.md`](../../CAREER_PLATFORM_ARCHITECTURE.md)) remains a later layer for scores and market history. It is out of scope for Agent v1.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Draft Project items only | Weak identity, poor linking, weaker Issue tooling |
| Labels as Status | Fragile Kanban; not Project SoT |
| SQLite/local JSON as SoT | Duplicates GitHub board state; drift |
| Telegram as SoT | Not searchable, not a board, not durable CRM |
| Big-bang rewrite of collectors | High risk; collectors already work |
| Intelligence scores in v1 | Premature without durable pipeline loop |

## Consequences

- Collectors never know workflow Status.
- Planner never scrapes; Reporter never calls GraphQL.
- Requires manual Project setup, PAT (`CAREER_AGENT_TOKEN`), and repo variables.
- Private repo recommended so Issues do not leak career notes.
- GraphQL field/option IDs are discovered at runtime from Project metadata.

## Related

- [Architecture](../architecture/career-agent.md)
- [GitHub setup guide](../github-setup-guide.md)
- [Migration plan](../migration-plan.md)
