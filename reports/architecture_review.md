# Architecture Review — iOS Hunter

**Audit date:** 2026-07-13  
**Mode:** Analysis only (no code changes, no commits)  
**Legend:** **[Fact]** repo evidence · **[Inference]** interpretation · **[Recommendation]** proposed change

---

## 1. One-line verdict

**[Inference]** iOS Hunter is a reliable **hourly vacancy notifier**, not a career intelligence platform. It optimizes for “did I already Telegram this URL?” and deliberately discards almost everything else.

**[Fact]** README: “Nothing else is sent. No match scores, cover letters, AI summaries, or market reports.”

---

## 2. Architecture (as implemented)

```text
GitHub Actions (hourly-trigger → collect.yml on macOS)
        │
   Swift JobHunter CLI
        │ fetches JobSource scrapers in parallel (sequential for-loop)
        │ writes database/swift_export.json
        ▼
   Python scripts/run_pipeline.py
        │ collector.companies.collect_all()
        │   + load Swift export
        │   + Teamtailor / Greenhouse / Ashby / Lever / Workable
        │   + DOU Top-50 career discovery
        │ parser.normalize → iOS filter
        │ parser.deduplicate
        │ database.seen (URL gate)
        ▼
   integrations.notify → Telegram
        │
   commit database/seen.json [skip ci]
```

**[Fact]** Documented in `ARCHITECTURE.md`, `.github/workflows/collect.yml`, `scripts/run_pipeline.py`.

### Design principles (stated)

| Principle | Evidence |
|-----------|----------|
| Zero-cost hosting | GitHub Actions + private repo |
| No backend / no LLM | ARCHITECTURE.md |
| Telegram only output | README + `integrations/notify.py` |
| Minimal durable state | URL → `{title, company, first_seen}` in `seen.json` |

**[Inference]** These principles conflict with a “career intelligence platform” goal. Platform ambitions require durable vacancy history, company metadata, and explainable scores — all absent by design.

---

## 3. Collectors

### Swift (`Sources/JobHunter/`)

**[Fact]**

- Protocol `JobSource`: `company`, `tier`, `fetchJobs()`.
- Registry: `JobSources.all(http:)` in `JobSource.swift` — **55 sources** in latest export meta (`sources_total: 55`).
- Mix of dedicated `*Source.swift` types and generics: `HTMLRegexJobSource`, `WorkableWidgetSource`, `AshbyJobBoardSource`, `TeamtailorJSONFeedSource`, `BreezyHRSource`.
- CLI exports JSON via `SwiftExport.write`.
- Latest export: **19 jobs**, **2 failed companies** (`Leobit`, `JetSoftPro`).

### Python (`collector/`)

**[Fact]**

- `companies.py`: Levi9, Avenga, Readdle, Preply, N-iX, ELEKS, Globaldev, Intetics, Intersog, Romexsoft, SupportYourApp + DOU Top-50.
- Overlap with Swift for Levi9, Avenga, N-iX, Eleks/ELEKS.
- Readdle / Preply / several Workable accounts are **Python-only**.

**[Inference]** Dual runtimes increase maintenance and create silent blind spots if Swift export fails but Python “healthy” sources still run (or vice versa).

---

## 4. Pipeline

**[Fact]** `scripts/run_pipeline.py`:

1. Load seen store (optional SQLite migrate — `jobs.db` currently **missing**).
2. Collect → normalize → dedupe.
3. Diff vs seen by canonical URL.
4. Telegram new vacancies **or** empty report with stats.
5. Mark seen only if `seed_only` or Telegram send succeeded.

**[Fact]** Seed mode: `SEED_SEEN_ONLY` / `--seed-only` marks without notify.

---

## 5. Company database

**[Fact]** There is **no company database**.

Companies exist only as:

- string literals on scrapers (`let company = "…"` / `company: "…"`),
- optional DOU slug overrides in `collector/dou.py` (`SLUG_OVERRIDES`),
- free-text `company` on vacancies in `seen.json`.

**[Fact]** No `active` / `archived` flags, aliases table, size, business model, remote policy, or career score persisted.

**[Inference]** “Company inventory” must be reconstructed by parsing Swift/Python source — brittle and incomplete for intelligence use cases.

---

## 6. Vacancy model

### Swift `Job`

**[Fact]** Fields: `title`, `url`, `company`, `location?`, `remote?`, `published?`, `source`, `description?`, computed `hash`.

### Python `Vacancy`

**[Fact]** Adds `canonical_url`, `source_job_id`, `identity_key`, `identity_strategy`, `published_at`.

### Persisted in `seen.json`

**[Fact]** Only `title`, `company`, `first_seen` per URL.

**[Inference]** Descriptions, remote, location, published dates, and tech signals are **thrown away** after notify. This makes Phases 4–6 (history, tech trends, salary from JDs) scientifically impossible from hunter history alone.

**[Fact]** Latest `swift_export.json`: **0 jobs with usable descriptions** (`description` empty / null across export).

---

## 7. Notification flow

**[Fact]** `integrations/notify.py`:

- Batches new vacancies into one Telegram message.
- Labels source via host suffix map (Ashby, Greenhouse, Lever, Workable, DOU, EPAM careers, …).
- Empty-run report includes found / seen / new / duplicates / failed sources.

**[Fact]** Order of vacancies in the message is collect order, not ranked.

---

## 8. Scoring

| Kind | Exists? | Evidence |
|------|---------|----------|
| Career / match score | **No** | README explicit denial |
| Scraper tier `JobSourceTier` | **Yes** | `tier1…tier3`, `product`, `legacy` — collect priority |
| Dedupe richness score | **Yes** | `parser/deduplicate.py` `_richness_score` — prefers longer description |

**[Inference]** Using `JobSourceTier` as a proxy for company quality is incorrect: `product` (4) sorts *after* `tier3` (3), so Grammarly scrapes with lower priority than Agiliway.

---

## 9. Filtering

**[Fact]** iOS filter: title (or description in Python path) must contain `ios` or `swift` (`Filter.swift`, `parser.normalize.is_ios_job`).

**[Fact]** No seniority filter, no QA/TPM denylist, no company allowlist.

**[Fact]** Current noise in seen/export titles includes Test Automation, Senior iOS Test Engineer, TPM (Java/Android/iOS), Mobile Automation QA.

**[Inference]** Filter is intentionally minimal and produces false positives for career-seeking Senior iOS engineers.

---

## 10. Deduplication

**[Fact]** Two layers:

1. Swift `Deduplicator` before export.
2. Python `deduplicate_with_report`: identity by `source_job_id` or canonical URL; also collapses same `company+title` keeping richer record.

**[Fact]** Seen gate is **URL-only** — reopen with new URL = new notify; same URL forever silence even if JD changes.

---

## 11. Application tracking

**[Fact]** **None** in iOS Hunter.

**[Fact]** Application/interview ledger lives externally in Profile `career/interview/pipeline.md` (not linked by hunter).

---

## 12. Recruiter tracking

**[Fact]** **None** in iOS Hunter (no contacts, response times, or ghosting metrics).

---

## 13. Reports

**[Fact]** Prior audit markdown exists under `reports/` from a previous session. Production pipeline does **not** generate reports.

**[Fact]** No scheduled market analytics, dashboards, or monthly digests in workflows.

---

## 14. Critical gaps vs “Career Intelligence Platform”

| Capability | Status | Severity |
|------------|--------|----------|
| Durable vacancy history with JD text | Missing | Critical |
| Company registry / metadata | Missing | Critical |
| Career scoring + explainability | Missing | Critical |
| Application / interview CRM | Missing (external only) | High |
| Recruiter intelligence | Missing | High |
| Tech / salary extraction | Impossible today (no descriptions stored) | Critical |
| Ranked notify | Missing | Medium |
| Trend detection (30/90/365d) | Impossible (seen spans ~1 day) | Critical |
| Djinni board coverage | Missing | High |

---

## 15. Recommendations (architecture direction)

1. **[Recommendation]** Introduce `companies.yaml` + `vacancies` history store **before** building dashboards.
2. **[Recommendation]** Persist normalized vacancy snapshots (title, description hash, tech tags, remote, salary if present) on every collect — not only URLs.
3. **[Recommendation]** Split `collect_priority` from `career_score`; never overload `JobSourceTier`.
4. **[Recommendation]** Keep Telegram as delivery; add optional weekly intelligence digest.
5. **[Recommendation]** Link to Profile interview pipeline via IDs — do not duplicate private recruiter data into a publicizable repo without a privacy boundary.

See `platform_recommendations.md` and `roadmap.md` for prioritized evolution.
