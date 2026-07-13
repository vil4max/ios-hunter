# Database Cleanup

**Audit date:** 2026-07-13  
**Legend:** **[Fact]** · **[Inference]** · **[Recommendation]**

---

## Duplicates

| Issue | Evidence | Recommendation |
|-------|----------|----------------|
| Genesis dual sources | Ashby + Breezy in `JobSource.swift` | Keep feeds; one `company_id` |
| Eleks vs ELEKS | Swift `Eleks`, Python `ELEKS` | Normalize `ELEKS` |
| Levi9 / Avenga / N-iX dual collect | Swift + Python | Single owner path |
| N-iX vs NIX | Hunter N-iX; Profile event NIX; DOU #12 vs #13 | **Never merge**; document aliases |

---

## Obsolete / low-value collectors

**[Inference]** Candidates to disable after 30 quiet days:

| Company | Why |
|---------|-----|
| SupportYourApp | BPO/support; Tier C score 22 |
| Zfort | Fragile title HTML; list URL as job URL |
| Romexsoft, Intersog, Globaldev, Intetics | Python long-tail |
| Intellectsoft, Lohika | Legacy weak signal |
| Solvd | Seen row is QA automation |

**[Fact]** Leobit & JetSoftPro **failed** in latest Swift export meta — reliability issue, not proof of death.

---

## Renamed / merged

| Old | New | Hunter |
|-----|-----|--------|
| Netpeak Group | FRACTAL | Missing record |
| Terrasoft | Creatio | Missing |
| Luxoft | DXC Luxoft | Slug only |
| Grammarly board | Ashby Superhuman | Handled in slug |

---

## No longer hiring iOS / almost none

**[Fact]** Cannot prove from 1-day seen store.  
**[Inference]** Many tier3 HTML farms produced **zero** rows in export/seen — either quiet or broken.

**[Recommendation]** Track `zero_hit_streak` per source; auto-disable after N failures or N empty collects.

---

## Broken metadata

| Breakage | Evidence |
|----------|----------|
| `remote` always null in export | 19/19 jobs `remote: None` |
| Descriptions empty | Export descriptions unused |
| Tier semantics inverted vs career value | `product` rawValue 4 > `tier3` 3 |
| No archived flag | Dead scrapers look “active” |
| QA/TPM pass iOS filter | Multiple seen titles |

---

## Missing metadata

See also architecture review. Minimum registry fields:

`id, name, aliases[], country, size_band, business_model, collect_priority, career_score, apply_tier, remote_policy, relocation, english, ai_focus, ats[], enabled, notes`

---

## Cleanup sequence **[Recommendation]**

1. Add registry; stop treating source lists as DB.  
2. Dedupe Swift/Python pairs.  
3. First-class Readdle/Preply.  
4. Add Luxoft, FRACTAL, Wix, Creatio.  
5. Title classifier denylist (qa, test engineer, tpm).  
6. Disable SupportYourApp + Zfort pending verify.  
7. Fix Eleks naming; document NIX ≠ N-iX.
