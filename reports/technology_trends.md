# Technology Trends

**Audit date:** 2026-07-13  
**Legend:** **[Fact]** · **[Inference]** · **[Recommendation]**

---

## Data availability

**[Fact]** Requested ranking by frequency across historical JDs **cannot be done** from iOS Hunter:

- `seen.json` stores only `title`, `company`, `first_seen`.
- Latest `swift_export.json`: **19 jobs, ~0 descriptions** (empty strings).
- Title-only corpus is 22 strings — statistically worthless for stack trends.

**[Fact]** Title keyword hits in combined seen+export titles:

| Token | Hits | Context |
|-------|-----:|---------|
| KMM / Kotlin Multiplatform | 2 | GlobalLogic Lead KMM; implied multiplatform |
| Android | 4 | Often dual-stack or noise (TPM, iOS+Android) |
| Swift (in title) | 1 | Andersen “iOS Developer (Swift)” |
| SwiftUI / UIKit / Concurrency / TCA / AI / LLM / … | **0** | Absent from titles |

**[Inference]** Absence in titles ≠ absence in JDs. Collectors often never populate `description` even when ATS provides HTML.

---

## External market signals (labeled inference)

Used only to avoid an empty report; **not** hunter evidence.

### Growing (market inference 2025–2026)

| Technology | Why it matters for Senior iOS |
|------------|-------------------------------|
| SwiftUI | Default for new feature work at product/US clients (e.g. Grid Dynamics role context in Profile diary) |
| Swift Concurrency / Swift 6 | Strict concurrency migrations in mature teams |
| AI-assisted engineering (Cursor, Copilot, agents) | Explicit in some JDs; SoftServe/EPAM AI hiring narratives (DOU) |
| On-device / voice AI | Niche premium; aligns with your GlobalLogic Watch Voice AI chapter |
| SPM modularization | Common in larger codebases |

### Stable / still required

| Technology | Note |
|------------|------|
| UIKit | Legacy + coexistence; still mandatory in many codebases |
| REST | Default networking |
| MVVM | Still dominant architecture label |
| XCTest / unit testing | Interview differentiator (Grid Dynamics feedback: testing gap) |
| CI (Bitrise / GHA / Fastlane) | Expected operational literacy |

### Declining as primary stack (inference)

| Technology | Note |
|------------|------|
| RxSwift as default | Replaced by Concurrency/Combine in many new projects |
| VIPER as default greenfield | Still appears in legacy outsourcing; rarely “modern” signal |
| Objective-C primary | Maintenance only |

### Rare but valuable

| Skill | Career value |
|-------|----------------|
| Swift 6 strict concurrency | Separates Senior from Mid in interviews |
| TCA / advanced architecture | Product/US client interviews |
| On-device ML / Audio / Watch | Thin supply |
| LLM product features + agent workflows | Matches your positioning goal |
| KMM | Appears in GL listings; dual-skill premium but dilutes pure iOS story |

---

## Collector failure modes for tech intel

**[Fact]** Export schema includes `description`, but scrapers leave it empty.  
**[Inference]** Tech intelligence requires either:

1. ATS JSON fields that include content (Greenhouse `content=true` already used in Python — but not persisted), or  
2. Description scraping + HTML→text + tag extraction at ingest.

**[Recommendation]** On every collect, extract and store tech tags via keyword/LLM classifier; keep raw description privately if needed.

---

## Provisional “most requested” list for your search (inference)

1. SwiftUI + UIKit coexistence  
2. Swift Concurrency  
3. Architecture / modular SPM  
4. Unit testing / CI  
5. AI-assisted delivery  
6. English communication  

Until hunter stores JD text, treat Djinni/LinkedIn samples as the real tech radar.
