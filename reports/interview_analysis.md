# Interview Analysis

**Audit date:** 2026-07-13  
**Legend:** **[Fact]** · **[Inference]** · **[Recommendation]**

---

## Repository boundary

**[Fact]** iOS Hunter contains **zero** interview-stage data, take-home flags, difficulty ratings, or candidate feedback.

**[Fact]** Interview intelligence for this audit comes from the **external** Profile repo:

- `career/interview/pipeline.md`
- `career/interview/companies/grid-dynamics-2026-senior-ios.md`

That data is **not wired** into hunter.

---

## Coverage matrix

| Company in hunter | Interview data exists? | Source |
|-------------------|------------------------|--------|
| Grid Dynamics | **Yes** | Profile pipeline + diary |
| All other hunter companies | **No** | — |
| NIX (not in hunter) | **Yes** (CV screen reject) | Profile pipeline |

---

## Grid Dynamics — Senior iOS (only rich record)

### Stages **[Fact]**

1. Recruiter outreach (2026-04-25…)  
2. Role pause/resume  
3. Recruiter screen (2026-05-05)  
4. Live technical interview (~1.5h expected; completed before 2026-05-15 feedback)  
5. Rejected

| Signal | Present? | Evidence |
|--------|----------|----------|
| Take-home | Not recorded | Diary: coding tasks not fully reconstructed |
| Architecture | Yes | Domain-Driven Modular Architecture in role context |
| SwiftUI | Yes | Mandatory for new features; UIKit legacy |
| Concurrency | Yes | Transition to Swift 6.2 / strict concurrency |
| AI | Yes | AI-assisted development in process |
| English | Implied (US client) | Role context |
| Live coding | Yes | Coding scored 5/10 |
| System design | Partial | Architecture/theory scored well (8/10 theory) |
| Candidate feedback | Yes | Via recruiter relay |
| Difficulty | High for T3 bar | Graded T2; role required T3 |

### Scores / feedback **[Fact — employer via recruiter]**

- Theory 8/10; Coding 5/10  
- Strengths: memory, threading, architecture, principles  
- Gaps: unit testing, project setup, coding clarity  
- Outcome: T2 (Middle) vs required T3 (Senior)

### Role tech (employer expectations) **[Fact]**

SwiftUI + UIKit · SPM modules · Swift 6.2 concurrency · Bitrise · unit tests · AI-assisted workflow · ~15 iOS engineers · retail/e-commerce US client

---

## NIX — Middle iOS **[Fact]**

- Applied Middle title; rejected at CV screening; **no interview**.  
- **[Inference]** Senior-positioned candidates applying Middle may lose on fit; n=1.

**[Fact]** NIX ≠ N-iX (hunter tracks N-iX only).

---

## All other companies

| Field | Value |
|-------|-------|
| interview stages | unknown |
| take-home / live / system design | unknown |
| SwiftUI / Concurrency / AI / English emphasis | unknown in hunter |
| difficulty | unknown |
| feedback | none |

**[Inference]** Do not invent interview playbooks per company without diary entries.

---

## Cross-cutting recommendations

1. **[Recommendation]** After each process, write `interview/companies/<id>.md` and link `company_id` in a future hunter CRM — bidirectional.  
2. **[Recommendation]** Practice loop prioritized by Grid Dynamics gaps: live coding, unit tests, project setup (already in Profile `technical.md`).  
3. **[Recommendation]** Skip Middle-titled applications unless strategic.  
4. **[Recommendation]** For Grid Dynamics re-entry: only explicit Senior/T3 scopes.
