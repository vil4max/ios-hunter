# Vacancy Intelligence

**Audit date:** 2026-07-13  
**Data window in repo:** `seen.json` first_seen **2026-07-10 only** (08:29–17:02 UTC)  
**Legend:** **[Fact]** · **[Inference]** · **[Recommendation]**

---

## Critical data limitation

**[Fact]** Historical store contains **22** vacancy URLs across **14** companies. All `first_seen` timestamps fall on a **single calendar day**.

**[Fact]** `seen.json` does **not** store: last_seen, closed_at, description, seniority enum, or salary.

**[Fact]** Therefore the following requested metrics **cannot be computed from repository data**:

| Metric | Status |
|--------|--------|
| last 30 / 90 / 365 days volume | Not meaningful (window ≪ 30d) |
| average vacancy lifetime | Impossible (no close events) |
| hiring trend / growth / decline | Impossible (n≈1 day) |
| true historical totals | Only “since seed/cutover”, not market history |

**[Inference]** Any multi-month trend claim from hunter alone would be fabricated. Below is a **snapshot census**, not a trend study.

**[Recommendation]** Persist vacancy snapshots every collect with `observed_at`, keep open/closed state, retain ≥12 months before claiming trends.

---

## Snapshot census (`seen.json`)

### Totals by company

| Company | Total vacancies (all-time in store) | Titles |
|---------|------------------------------------:|--------|
| GlobalLogic | 5 | Senior iOS SWE; Senior iOS Test; TPM Java/Android/iOS; Lead KMM; iOS+Android |
| Intellias | 2 | Middle iOS; Senior iOS |
| EPAM | 2 | Senior iOS Developer; Senior SWE iOS |
| N-iX | 2 | Lead iOS; Middle iOS |
| Grid Dynamics | 2 | iOS Developer; Mobile Automation QA |
| Genesis | 1 | iOS Developer |
| Solvd | 1 | Test Automation Engineer (iOS) |
| KissMyApps | 1 | iOS Engineer |
| Uklon | 1 | iOS Engineer Senior |
| ZONE3000 | 1 | Middle+/Senior Mobile iOS |
| Levi9 | 1 | Senior iOS Developer |
| Onix Systems | 1 | Senior iOS Developer |
| Andersen | 1 | iOS Developer (Swift) Kazakhstan |
| DataArt | 1 | iOS Developer, Mobile Ticketing |
| **Total** | **22** | |

### Last 30 / 90 / year

**[Fact]** All 22 observations ∈ last 30 days (and last 90 / year) because the store began ~2026-07-10.

| Window | Vacancies observed | Interpretation |
|--------|-------------------:|----------------|
| Last 30d | 22 | = entire history |
| Last 90d | 22 | = entire history |
| Last year | 22 | = entire history |

### Vacancy lifetime

**[Fact]** Not available.  
**[Inference]** Cannot estimate; URLs remain forever once seen even if role closed.

### Hiring trend / growth / decline

**[Fact]** Insufficient time series.  
**[Inference from external DOU, not hunter]:** product employers growing headcount; large outsourcing flat-to-cautious — do not project onto iOS vacancy counts without board data.

### Common titles (frequency in seen)

| Pattern | Count | Notes |
|---------|------:|-------|
| Senior* iOS / SWE iOS | 9 | Dominant useful signal |
| Middle* | 2 | |
| Lead* | 2 | Lead iOS; Lead KMM |
| Unspecified “iOS Developer/Engineer” | 5 | |
| QA / Test / Automation | 3 | Noise for eng search |
| TPM | 1 | Noise |

### Average seniority (heuristic on titles)

**[Fact — heuristic counts]**

| Bucket | Count | Share |
|--------|------:|------:|
| senior | 9 | 41% |
| lead+ | 2 | 9% |
| middle | 2 | 9% |
| unspecified | 9 | 41% |

**[Inference]** ~50% of notified rows are clearly Senior/Lead; ~27% are explicit noise or Mid; unspecified need JD reading (not stored).

---

## Live export cross-check (`swift_export.json`)

**[Fact]** Latest export: **19** jobs, **12** companies; failed scrapers: Leobit, JetSoftPro.

**[Fact]** Companies in export but not in seen: **Ciklum** (Senior iOS Engineer).  
**[Inference]** Likely already seen under different URL identity or timing race — verify manually; export is not a historical ledger.

**[Fact]** `remote` field is `null` for all 19 export jobs — remote intelligence not collected at source.

---

## Most active employers (within tiny sample)

**[Fact]** By seen count: GlobalLogic (5) ≫ others (1–2).

**[Inference]** This measures **scraper yield + seed day market**, not true market share. GlobalLogic’s multi-role page also emits QA/TPM/KMM noise, inflating counts.

---

## Recommendations

1. **[Recommendation]** Store `observations[]` per URL with timestamps to enable lifetime and trend.  
2. **[Recommendation]** Classify titles (`seniority`, `role_family: eng|qa|mgmt`) at ingest.  
3. **[Recommendation]** Drop or quarantine QA/TPM from career notify path.  
4. **[Recommendation]** Do not publish “hiring trend” dashboards until ≥90 days of observation history exists.
