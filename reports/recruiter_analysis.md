# Recruiter Analysis

**Audit date:** 2026-07-13  
**Legend:** **[Fact]** · **[Inference]** · **[Recommendation]**

---

## Repository evidence

**[Fact]** iOS Hunter has **no recruiter entities**, contacts, response-time metrics, ghosting flags, or CRM tables.

**[Fact]** Notify layer only maps **ATS host → label** (`integrations/notify.py`), e.g. Ashby, Greenhouse, Lever, Workable, DOU, EPAM careers.

**[Fact]** Observed hosts from seen + export URLs:

| Host / ATS | Example companies |
|------------|-------------------|
| www.globallogic.com | GlobalLogic |
| careers.epam.com | EPAM |
| careers.n-ix.com / Greenhouse | N-iX |
| jobs.ashbyhq.com | Solvd, KissMyApps, (Grammarly Superhuman board) |
| gen-tech.breezy.hr | Genesis |
| www.griddynamics.com | Grid Dynamics |
| career.intellias.com | Intellias |
| explore-jobs.ciklum.com | Ciklum |
| jobs.ua.levi9.com | Levi9 |
| people.andersenlab.com | Andersen |
| www.dataart.team | DataArt |
| jobs.dou.ua | Uklon, ZONE3000 |
| apply.workable.com (Python) | BetterMe, Lohika, … |
| boards-api.greenhouse.io (Python) | Readdle, N-iX |

---

## Recruiter intelligence (external / sparse)

### Grid Dynamics **[Fact — Profile]**

| Field | Value |
|-------|-------|
| Known recruiters | Not named in stored diary (private channel) |
| Channel | Recruiter outreach |
| Response behavior | Active through process; feedback delivered 2026-05-15 |
| Ghosting | No — closed with graded outcome |
| Avg response time | Not quantified |
| ATS | Company careers site |

### NIX **[Fact — Profile]**

| Field | Value |
|-------|-------|
| Channel | Application → HR email rejection |
| Interview | None |
| Ghosting | No (explicit reject) |

### All other hunter companies

| Field | Value |
|-------|-------|
| known recruiters | unknown |
| response rate / ghosting / avg response | **no data** |
| known ATS | inferable from URL host only |

---

## Inferences

1. **[Inference]** ATS diversity is high; a recruiter CRM must key off `company_id` + `channel` (Djinni, LinkedIn, outreach, ATS apply), not hunter alone.  
2. **[Inference]** “Ghosting rate” requires application events with timestamps — belongs in Profile pipeline, optionally synced.  
3. **[Inference]** Djinni anonymous apply will dominate UA search; hunter currently ignores that channel’s recruiter dynamics.

---

## Recommendations

1. **[Recommendation]** Keep recruiter PII in **gitignored / Profile-private** storage.  
2. **[Recommendation]** Schema: `recruiter {id, company_id, name, channels[], last_contact, response_hours[], outcome_tags[]}`.  
3. **[Recommendation]** Auto-suggest ATS from vacancy URL host (already partially implemented in notify).  
4. **[Recommendation]** Do not block platform roadmap on recruiter scraping — manual logging after each touch is enough for n≈10 processes/quarter.
