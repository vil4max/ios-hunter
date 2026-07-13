# Platform Recommendations

**Audit date:** 2026-07-13  
**Goal:** Vacancy collector → Career intelligence platform  
**Constraint:** Prefer data quality, score explainability, actionable output over “collect everything”

Complexity: **L** low · **M** medium · **H** high

---

## 1. Better company model

**Problem:** Companies are stringly-typed scrapers.  
**Benefit:** Stable IDs, tiers, scores, enable/disable, aliases (N-iX ≠ NIX).  
**Complexity:** M  
**Deps:** None  
**ROI:** Critical foundation  

**Shape:** `companies.yaml` → validated schema → loaded by Swift/Python.

---

## 2. Better vacancy model

**Problem:** History is URL→{title,company,first_seen}; descriptions discarded.  
**Benefit:** Tech trends, salary parse, lifetime, seniority stats become possible.  
**Complexity:** M–H  
**Deps:** Company model; storage (JSONL/SQLite)  
**ROI:** Critical for Phases 4–6 automation  

Persist per observation: url, company_id, title, description_text|hash, remote, location, published_at, observed_at, tech_tags[], salary_parsed?, seniority, role_family.

---

## 3. Better recruiter model

**Problem:** No CRM in hunter; private data lives in Profile.  
**Benefit:** Response/ghosting analytics; outreach memory.  
**Complexity:** M  
**Deps:** Privacy boundary (gitignore / Profile link)  
**ROI:** Medium (manual log enough at low volume)

---

## 4. Better scoring

**Problem:** No career score; `JobSourceTier` misused mentally.  
**Benefit:** Ranked Telegram; explainable “why this company”.  
**Complexity:** M  
**Deps:** Company registry  
**ROI:** High  

Use versioned rubric from `company_scoring.md`; show top drivers per vacancy.

---

## 5. Better search / filtering

**Problem:** ios|swift substring admits QA/TPM.  
**Benefit:** Higher signal notify.  
**Complexity:** L  
**Deps:** None  
**ROI:** High quick win  

Add role_family classifier + Senior+ boost + company tier filter.

---

## 6. Better reporting

**Problem:** Manual audits only.  
**Benefit:** Weekly/monthly markdown or Telegram digest.  
**Complexity:** M  
**Deps:** Vacancy history ≥30 days  
**ROI:** High once data exists  

---

## 7. Career dashboard

**Problem:** No single view of market vs goals.  
**Benefit:** Executive situational awareness.  
**Complexity:** H (if web) / M (if markdown CI artifact)  
**Deps:** History + scores  
**ROI:** Medium — start with generated `reports/executive_dashboard.md` in CI monthly

---

## 8. Market analytics & trend detection

**Problem:** 1-day store cannot trend.  
**Benefit:** Growth/decline employers, tech waves.  
**Complexity:** H  
**Deps:** ≥90 days vacancy observations  
**ROI:** High later; **do not build now**

---

## 9. AI adoption & technology tracking

**Problem:** Empty descriptions ⇒ zero tags.  
**Benefit:** Align apply strategy to SwiftUI/Concurrency/AI demand.  
**Complexity:** M  
**Deps:** Description capture + tagger  
**ROI:** High for your AI-native positioning  

---

## 10. Application / interview bridge

**Problem:** Hunter notify ≠ Profile pipeline.  
**Benefit:** Closed-loop “saw → applied → outcome → score calibration”.  
**Complexity:** M  
**Deps:** Profile pipeline schema  
**ROI:** High for personal strategy  

---

## Prioritized build order

| Priority | Item | Complexity |
|---------:|------|:----------:|
| 1 | Title denylist + Senior bias in notify | L |
| 2 | Company registry + career_score | M |
| 3 | Persist vacancy snapshots + tech tags | M |
| 4 | Ranked Telegram by score | L–M |
| 5 | First-class Tier S sources (Readdle, Preply, Luxoft, Wix, …) | M |
| 6 | Weekly markdown intelligence job | M |
| 7 | Profile pipeline sync | M |
| 8 | Trend dashboards | H |
| 9 | Full web career dashboard | H |

**Anti-goals:** LLM cover letters in-band, scraping Djinni at any cost, scoring without explainability, storing recruiter PII in a shareable repo.
