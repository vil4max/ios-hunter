# Market Gap Analysis

**Audit date:** 2026-07-13  
**Market refs:** DOU Top-50 Winter 2026 (Jan 2026), DOU article on cautious hiring, Djinni employer list  
**Legend:** **[Fact]** · **[Inference]** · **[Recommendation]**

---

## Market health (external)

**[Fact — DOU]** Top-50 headcount ~79.8k (+0.5% YoY); hiring cautious; product firms drive growth (Ajax, Genesis, mono, FRACTAL, …).  
**[Fact — DOU]** EPAM first growth since 2022; SoftServe/GlobalLogic roughly flat; Luxoft −100 (legalization/bench).  
**[Inference]** Senior+ and AI/Cloud skills are the service-side hiring filter; volume Middle roles are competitive and compressed.

---

## Checklist coverage

| Employer | In hunter? | Evidence | Gap severity |
|----------|------------|----------|--------------|
| GlobalLogic | Yes | Swift scraper; 5 seen URLs | Low |
| SKELAR | Yes | Ashby | Low |
| N-iX | Yes | Swift + Greenhouse; 2 seen | Low |
| Luxoft | **No dedicated** | Only `DXC Luxoft` in DOU `SLUG_OVERRIDES` | **High** |
| EPAM | Yes | Swift; 2 seen | Low |
| Intellias | Yes | Swift; 2 seen | Low |
| Sigma Software | Yes | Swift; code tier3 | Medium (under-prioritized) |
| SoftServe | Yes | Swift; legacy tier | Medium (under-prioritized) |
| Avenga | Yes | Swift+Python | Low |
| Grid Dynamics | Yes | Swift; 2 seen | Low |
| DataArt | Yes | Swift; 1 seen | Low |
| Genesis | Yes | Ashby+Breezy; 1 seen | Low |
| Boosta | **No** | — | Medium |
| FRACTAL | **No** | DOU #17 rename from Netpeak; slug only | **High** |
| Brights | **No** | — | Low |
| DOIT Software | **No** | — | Low |
| Adaptiq | **No** | — | Low |
| Readdle | Python-only | Greenhouse in `companies.py` | **High** (fragile) |
| Grammarly | Yes | Ashby `Superhuman` | Low |
| Creatio | **No** | — | High (product/AI) |
| Wix | **No dedicated** | DOU #36 + slug override | **High** |
| Snap | **No** | — | High (Tier S) |
| GitLab | **No** | — | High (Tier S) |
| Amazon | **No** | — | Medium (rare/hard) |
| Preply | Python-only | Ashby | **High** (fragile) |
| MacPaw | Yes | Swift | Low |
| Ajax Systems | Yes | Ashby | Low |
| Petcube | **No** | — | Medium (product IoT) |
| Jooble | **No** | — | Medium (product) |

---

## Why missing employers are missing

### Structural **[Fact]**

1. Companies are added only by writing scrapers — no registry onboarding.
2. No Djinni collector — international employers that post primarily on Djinni never appear.
3. DOU Top-50 discovery is opportunistic (career-site parse), not a durable company record.
4. Product/international firms with custom ATS were never prioritized vs UA outsourcing HTML pages.

### Per missing employer **[Inference]**

| Employer | Why absent |
|----------|------------|
| Luxoft | Never implemented `JobSource`; DOU override alone does not persist monitoring |
| FRACTAL | Rebrand Winter 2026; no scraper update after Netpeak rename |
| Wix / Creatio / Petcube / Jooble | Product firms without dedicated ATS wiring |
| Snap / GitLab / Amazon | International; architecture assumes UA career pages |
| Boosta / Brights / DOIT / Adaptiq | Small or sporadic iOS; never prioritized |
| Readdle / Preply “gap” | Present in Python only — **operational gap**, not absolute absence |

### Name collision **[Fact + Inference]**

- Hunter tracks **N-iX**.  
- Profile pipeline records rejection from **NIX** (Kharkiv, DOU #12) — **different company**.  
- **[Recommendation]** Never alias NIX ↔ N-iX.

---

## Coverage vs DOU Top-50

**[Fact]** Dedicated scrapers cover roughly the service giants + selected product (EPAM, SoftServe, GL, Ajax, Genesis, DataArt, Intellias, Ciklum, N-iX, Sigma, ELEKS, Avenga, Grid Dynamics, SPD, SKELAR, …).

**[Fact]** ~30 Top-50 names have no durable hunter source (Luxoft, Evoplay, NIX, FRACTAL, Nova Digital, mono, Wix, MEGOGO, …).

**[Inference]** Hunter overfits to “easy HTML career pages” and underfits “highest career ROI employers.”

---

## Recommendations

1. **[Recommendation]** Add Luxoft, Wix, Creatio, FRACTAL as first-class sources.  
2. **[Recommendation]** Promote Readdle & Preply to Swift or shared config.  
3. **[Recommendation]** Add Djinni (or Greenhouse/Ashby watchlist) for Snap/GitLab/BlaBlaCar/Amazon.  
4. **[Recommendation]** Track Petcube & Jooble if Senior iOS + English appears on boards.  
5. **[Recommendation]** Stop measuring coverage by scraper count; measure by Tier S/A hit rate.
