# Roadmap — Collector → Career Intelligence Platform

**Audit date:** 2026-07-13  
**Principles:** maintainability · data quality · explainable scores · actionable recommendations · **not** maximal scraping

No production code changes in this audit.

---

## North star

```text
Vacancy Collector (today)
        ↓
Signal Radar (ranked, filtered, company-aware)
        ↓
Career Intelligence Platform (history, scores, weekly briefs, closed-loop with applications)
```

---

## Phase 0 — Reality lock (done via this audit)

Document gaps; refuse fake trends from 1-day data.

---

## Feature backlog (impact-ranked)

### F1 — Notify signal hygiene

| | |
|--|--|
| **Problem** | QA/TPM/Middle noise equals eng roles in Telegram |
| **Benefit** | Attention on $4–5k Senior paths |
| **Complexity** | Low |
| **Dependencies** | None |
| **Expected ROI** | Very high / immediate |

### F2 — Company registry + career_score

| | |
|--|--|
| **Problem** | No company DB; tiers ≠ career fit |
| **Benefit** | Explainable ranking; enable/disable; aliases |
| **Complexity** | Medium |
| **Dependencies** | Schema decision |
| **Expected ROI** | Critical foundation |

### F3 — Ranked Telegram

| | |
|--|--|
| **Problem** | FIFO URLs bury Grammarly behind Agiliway |
| **Benefit** | Actionable daily triage |
| **Complexity** | Low–Medium |
| **Dependencies** | F2 |
| **Expected ROI** | High |

### F4 — Vacancy snapshot persistence

| | |
|--|--|
| **Problem** | Descriptions/tech/remote discarded |
| **Benefit** | Enables tech/salary/lifetime analytics |
| **Complexity** | Medium |
| **Dependencies** | Storage format; privacy |
| **Expected ROI** | Critical for platform claim |

### F5 — Tech tag extraction

| | |
|--|--|
| **Problem** | Zero stack intelligence |
| **Benefit** | SwiftUI/Concurrency/AI demand tracking |
| **Complexity** | Medium |
| **Dependencies** | F4 |
| **Expected ROI** | High for AI-native positioning |

### F6 — First-class Tier S/A sources

| | |
|--|--|
| **Problem** | Readdle/Preply fragile; Luxoft/Wix/Creatio/FRACTAL/Snap/GitLab missing |
| **Benefit** | Radar matches personal strategy |
| **Complexity** | Medium (each ATS adapter) |
| **Dependencies** | F2 helpful |
| **Expected ROI** | High |

### F7 — Weekly intelligence digest

| | |
|--|--|
| **Problem** | Audits are manual and stale |
| **Benefit** | Executive dashboard cadence |
| **Complexity** | Medium |
| **Dependencies** | F2 + F4 (≥30 days data) |
| **Expected ROI** | High after data matures |

### F8 — Application closed loop

| | |
|--|--|
| **Problem** | Notify ≠ apply ≠ outcome |
| **Benefit** | Calibrate scores; stop repeating NIX/GD mistakes |
| **Complexity** | Medium |
| **Dependencies** | Profile pipeline link |
| **Expected ROI** | High personal |

### F9 — Trend engine (30/90/365)

| | |
|--|--|
| **Problem** | Cannot detect growth/decline employers |
| **Benefit** | True market analytics |
| **Complexity** | High |
| **Dependencies** | F4 + ≥90 days |
| **Expected ROI** | High later; **defer** |

### F10 — Web career dashboard

| | |
|--|--|
| **Problem** | Markdown/Telegram limited UX |
| **Benefit** | Rich exploration |
| **Complexity** | High |
| **Dependencies** | F2–F7 |
| **Expected ROI** | Medium — optional |

### F11 — Recruiter CRM

| | |
|--|--|
| **Problem** | No response/ghost metrics |
| **Benefit** | Soft-channel memory |
| **Complexity** | Medium |
| **Dependencies** | Privacy store |
| **Expected ROI** | Medium — manual OK first |

### F12 — Djinni integration

| | |
|--|--|
| **Problem** | Intl Tier S invisible |
| **Benefit** | Coverage completeness |
| **Complexity** | High (ToS/auth/fragility) |
| **Dependencies** | Legal/ToS review |
| **Expected ROI** | High if compliant; else manual watchlist |

---

## Suggested timeline

| Horizon | Deliver |
|---------|---------|
| Week 1–2 | F1 + start F2 |
| Week 3–4 | F3 + F6 (Readdle/Preply/Luxoft/Wix) |
| Month 2 | F4 + F5 |
| Month 3 | F7 + F8 |
| Month 4+ | F9; consider F10/F12 |

---

## Success criteria

1. ≥70% of Telegram items are Tier S/A Senior eng roles.  
2. Every company score shows top 3 weighted drivers.  
3. No trend charts until 90 days of snapshots.  
4. Personal apply list matches `personal_strategy.md` Top 20.  
5. Hunter remains zero-cost operable on GitHub Actions.

---

## Explicit non-goals (near term)

- Auto cover letters / LLM spam applies  
- Storing private recruiter PII in a shareable git history  
- Claiming “market trends” from `seen.json` as it exists today  
- Rewriting all HTML scrapers before registry exists
