# Salary Analysis

**Audit date:** 2026-07-13  
**Target band (you):** **$4,000–$5,000 USD / month**  
**Legend:** **[Fact]** · **[Inference]** · **[Recommendation]**

---

## Repository evidence

**[Fact]** iOS Hunter stores **no salary fields** on vacancies or companies.  
**[Fact]** Telegram messages do not include compensation.  
**[Fact]** Titles in `seen.json` / export contain **no** `$` / `USD` salary tokens.

⇒ All numbers below are **market estimates**, not extracted offers.

---

## Market anchors (external)

**[Inference — public 2026 guides / Djinni-style bands]**

| Segment | Typical Senior iOS monthly USD |
|---------|-------------------------------:|
| UA outsourcing mid | 2,800 – 4,000 |
| UA strong service / EU delivery | 3,500 – 5,000 |
| UA premium product | 4,500 – 7,000+ |
| Western remote / intl product | 5,000 – 8,000+ |

Your **$4–5k** target sits at the **upper domestic / lower international** boundary — realistic at strong service firms and mid product; easier at Grammarly/Readdle/Wix/remote intl.

---

## Company estimates

Confidence: **L** = low (brand only) · **M** = medium (segment + DOU size) · **H** = high (would need live offers — none in repo).

Transparency: **none in hunter**; “public” means employers sometimes post ranges on Djinni.

| Company | Min | Median | Max | Conf | Transparency | Trend (inference) | Fit to $4–5k |
|---------|----:|-------:|----:|------|--------------|-------------------|--------------|
| Grammarly | 5.5k | 7.0k | 9k+ | M | low–med | stable/up | Above target (good) |
| Readdle | 4.5k | 5.5k | 7k | M | low | stable | On/above |
| MacPaw | 4.0k | 5.2k | 6.5k | M | low | stable | On target |
| Preply | 4.5k | 5.5k | 7k | M | low | stable | On/above |
| Wix | 4.5k | 5.5k | 7.5k | M | low | stable | On/above |
| Ajax | 3.8k | 4.8k | 6.0k | M | low | up (headcount) | On target |
| Genesis | 4.0k | 5.5k | 7.5k | M | low | up | On/above |
| SKELAR | 3.5k | 4.8k | 6.5k | L | low | up | Borderline–on |
| SoftServe | 3.5k | 4.5k | 6.0k | M | low | flat | On target if Senior+ |
| EPAM | 3.3k | 4.3k | 5.8k | M | low | slight up | Reachable Senior+ |
| GlobalLogic | 3.3k | 4.2k | 5.5k | M | low | flat | Reachable; you know bar |
| Intellias | 3.3k | 4.2k | 5.5k | M | low | flat | Reachable |
| N-iX | 3.2k | 4.0k | 5.3k | M | low | flat | Lower edge |
| Luxoft | 3.3k | 4.2k | 5.5k | L | low | flat/down headcount | Reachable |
| Ciklum | 3.2k | 4.0k | 5.2k | M | low | flat | Lower edge |
| Sigma | 3.2k | 4.0k | 5.2k | M | low | flat | Lower edge |
| DataArt | 3.0k | 3.9k | 5.0k | M | low | flat | Stretch |
| Grid Dynamics | 3.5k | 4.5k | 6.0k | M | low | flat | On target if T3 Senior |
| Eleks | 3.2k | 4.0k | 5.2k | M | low | flat | Lower edge |
| Levi9 | 3.3k | 4.2k | 5.5k | M | low | flat | Reachable |
| BetterMe | 3.5k | 4.5k | 6.0k | L | low | unk | On target |
| KissMyApps | 3.5k | 4.5k | 6.0k | L | low | unk | On target |
| Avenga | 3.0k | 3.8k | 4.8k | L | low | flat | Risk below target |
| Yalantis | 3.0k | 3.8k | 4.8k | L | low | flat | Risk below |
| Andersen / Onix / long-tail | 2.5k | 3.3k | 4.2k | L | low | down pressure | **Often below target** |
| SupportYourApp / micro HTML | 2.2k | 3.0k | 3.8k | L | none | unk | Misaligned |

Trend column is **headcount/market inference**, not measured offer time series.

---

## Salary strategy implications

**[Inference]**

1. Hitting **$4–5k** reliably ⇒ prioritize Tier S/A product + top service Senior+; deprioritize long-tail outsourcing.  
2. Grid Dynamics can clear the band **only** at true Senior (T3) leveling — prior T2 outcome is a process risk, not a pay ceiling.  
3. Western-remote Tier S may exceed target; still pursue for relo/English/AI upside.

**[Recommendation]** Capture offered/expected salary in Profile pipeline events; never expect hunter to invent precision without JD parsing + offer CRM.
