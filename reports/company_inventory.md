# Company Inventory

**Audit date:** 2026-07-13  
**Sources of truth in repo:** Swift `JobSources.all`, Python `collect_all`, DOU overrides, `seen.json`, `swift_export.json`  
**Legend:** **[Fact]** · **[Inference]** · **[Recommendation]**

---

## Representation model

**[Fact]** Companies are scraper labels, not first-class records. Fields below marked `n/a` are **not stored** in the repository.

| Requested field | In repo? |
|-----------------|----------|
| name | Yes (string on scraper / vacancy) |
| aliases | No |
| source | Yes (implicit: Swift type / Python collector / DOU) |
| country | No |
| company size | No |
| business model | No |
| active / archived | No (scraper present ⇒ treated active) |
| priority | Partial — `JobSourceTier` only |
| score | No career score |
| remote / relocation / English / AI | No company-level fields |
| notes | No |

**[Inference]** Inventory values for country, size, model, remote, relo, English, AI are **external market inferences** for planning only — not hunter data.

---

## Summary counts

| Bucket | Count | Evidence |
|--------|------:|----------|
| Unique Swift company names | 54 | Parsed from `JobSource.swift` + `*Source.swift` |
| Python-only extras | 6 | Readdle, Preply, Globaldev, Intetics, Intersog, Romexsoft, SupportYourApp (− overlaps) |
| DOU-seen without dedicated scraper | 2 | Uklon, ZONE3000 in `seen.json` |
| Companies with ≥1 seen vacancy | 14 | `seen.json` |
| Companies with ≥1 job in latest export | 12 | `swift_export.json` |

---

## Inventory table

Priority = code `JobSourceTier` or `python-only` / `dou-only`.  
Score = career score from this audit (`company_scoring.md`), not production.  
Size = DOU Winter 2026 headcount when in Top-50, else `unknown`.

| Name | Aliases | Source | Country | Size (DOU) | Model | Active | Arch | Priority | Score | Remote | Relo | EN | AI | Notes |
|------|---------|--------|---------|------------|-------|--------|------|----------|------:|--------|------|----|----|-------|
| Ajax Systems | Ajax | Swift Ashby | UA | 4612 | Product | yes | no | product | 74 | hybrid | med | med | med | DOU #4 |
| Agiliway | — | Swift | UA | unk | Outsourcing | yes | no | tier3 | 32 | rem | low | low | low | |
| AltexSoft | — | Swift HTML | UA/US | unk | Outsourcing | yes | no | legacy | 40 | rem | low | med | low | |
| Andersen | Andersen Lab | Swift | UA/EU | unk | Outsourcing | yes | no | tier1 | 44 | rem | med | med | low | Seen KZ role |
| Apriorit | — | Swift Workable | UA | unk | Outsourcing | yes | no | tier3 | 34 | rem | low | med | low | |
| Avenga | — | Swift+Py Teamtailor | UA/PL | 873 | Outsourcing | yes | no | tier3 | 50 | rem | med | med | low | DOU #26 |
| BetterMe | — | Swift Workable | UA | unk | Product | yes | no | product | 66 | hybrid | low | med | med | |
| Binary Studio | — | Swift HTML | UA | unk | Outsourcing | yes | no | tier2 | 38 | rem | low | med | low | |
| CHI Software | — | Swift HTML | UA | unk | Outsourcing | yes | no | tier2 | 36 | rem | low | low | low | |
| Ciklum | — | Swift | UA | 1955 | Outsourcing | yes | no | tier3 | 57 | rem | med | med | med | DOU #11; under-prioritized |
| Computools | — | Swift HTML | UA | unk | Outsourcing | yes | no | tier3 | 30 | rem | low | low | low | |
| DataArt | — | Swift | UA | 2106 | Outsourcing | yes | no | legacy | 54 | rem | med | med | low | DOU #9 |
| Dev.Pro | DevPro | Swift | UA | unk | Outsourcing | yes | no | tier1 | 40 | rem | low | med | low | |
| Devlight | — | Swift | UA | unk | Outsourcing | yes | no | tier3 | 41 | rem | low | med | low | Mobile boutique |
| Eleks | ELEKS | Swift+Py Lever | UA | 1605 | Outsourcing | yes | no | tier1 | 56 | rem | med | med | med | Name casing split |
| EPAM | EPAM Ukraine | Swift | UA | 9560 | Outsourcing/Enterprise | yes | no | legacy | 68 | rem | high | high | high | DOU #1 |
| Exoft | — | Swift | UA | unk | Outsourcing | yes | no | tier2 | 34 | rem | low | low | low | |
| Genesis | Gen Tech | Swift Ashby+Breezy | UA | 3274 | Product holding | yes | no | product | 70 | hybrid | low | med | med | Dual ATS |
| Geniusee | — | Swift Workable | UA | unk | Product/Services | yes | no | product | 46 | rem | low | med | low | |
| GlobalLogic | GL / Hitachi | Swift | UA | 5425 | Outsourcing/R&D | yes | no | legacy | 67 | rem | high | high | high | DOU #3; recent employer |
| Globaldev Group | — | Py Workable | UA | unk | Outsourcing | yes | no | python | 33 | rem | low | low | low | |
| Grammarly | Superhuman board | Swift Ashby | UA/US | unk | Product | yes | no | product | 94 | rem | high | high | high | Board slug Superhuman |
| Grid Dynamics | — | Swift | UA/US | 700 | Outsourcing | yes | no | legacy | 58 | rem | med | high | med | Interview history external |
| Infopulse | — | Swift | UA | unk | Outsourcing | yes | no | tier3 | 42 | rem | med | med | low | Not in DOU top50 |
| Innovecs | — | Swift | UA | unk | Outsourcing | yes | no | tier3 | 40 | rem | low | med | low | |
| Inoxoft | — | Swift HTML | UA | unk | Outsourcing | yes | no | tier3 | 30 | rem | low | low | low | |
| Intellectsoft | — | Swift | UA | unk | Outsourcing | yes | no | legacy | 36 | rem | low | med | low | |
| Intellias | — | Swift | UA | 2022 | Outsourcing | yes | no | tier1 | 60 | rem | high | high | med | DOU #10 |
| Intetics | — | Py Workable | UA/US | unk | Outsourcing | yes | no | python | 34 | rem | low | med | low | |
| Intersog | — | Py Workable | UA/US | unk | Outsourcing | yes | no | python | 32 | rem | low | med | low | |
| Inverita | — | Swift HTML | UA | unk | Outsourcing | yes | no | tier3 | 30 | rem | low | low | low | |
| JetSoftPro | — | Swift HTML | UA | unk | Outsourcing | yes | no | tier3 | 33 | rem | low | med | med | Failed in last Swift run |
| KindGeek | — | Swift Workable | UA | unk | Outsourcing | yes | no | tier3 | 32 | rem | low | low | low | |
| KissMyApps | — | Swift Ashby | UA | unk | Product/Startup | yes | no | product | 54 | hybrid | low | med | med | |
| Leobit | — | Swift | UA | unk | Outsourcing | yes | no | tier1 | 39 | rem | low | med | low | Failed last Swift run |
| Levi9 | — | Swift+Py Teamtailor | UA/NL | unk | Outsourcing | yes | no | tier2 | 53 | rem | high | high | low | |
| Lohika | — | Swift Workable | UA/US | unk | Outsourcing | yes | no | legacy | 38 | rem | low | med | low | Possibly stale |
| MWDN | — | Swift | UA | unk | Outsourcing | yes | no | tier2 | 35 | rem | low | low | low | |
| MacPaw | — | Swift | UA | unk | Product | yes | no | product | 82 | hybrid | low | med | med | |
| Mind Studios | — | Swift HTML | UA | unk | Product studio | yes | no | product | 48 | rem | low | med | low | |
| N-iX | NIX? **no** | Swift+Py Greenhouse | UA | 1775 | Outsourcing | yes | no | tier1 | 58 | rem | med | high | med | ≠ NIX (Kharkiv) |
| Nortal | — | Swift | EE/UA | unk | Consulting | yes | no | tier2 | 53 | hybrid | high | high | med | |
| Onix Systems | Onix | Swift | UA | unk | Outsourcing | yes | no | tier2 | 42 | rem | low | med | low | |
| Otakoyi | — | Swift HTML | UA | unk | Outsourcing | yes | no | tier3 | 29 | rem | low | low | low | |
| Preply | — | Py Ashby | UA/global | unk | Product | yes | no | python | 79 | rem | high | high | med | Fragile path |
| QArea | — | Swift | UA | unk | Outsourcing | yes | no | tier2 | 35 | rem | low | low | low | |
| RBI Retail Innovation | RBI | Swift | AT/UA | unk | Product/Fintech | yes | no | product | 64 | hybrid | high | high | med | |
| Readdle | — | Py Greenhouse | UA | unk | Product | yes | no | python | 86 | hybrid | med | high | med | Fragile path |
| Romexsoft | — | Py Workable | UA | unk | Outsourcing | yes | no | python | 31 | rem | low | low | low | |
| SKELAR | — | Swift Ashby | UA | 1150 | Product holding | yes | no | product | 65 | hybrid | low | med | med | DOU #18 |
| SPD Technology | SPD | Swift | UA | 631 | Outsourcing | yes | no | tier1 | 43 | rem | low | med | low | DOU #45 |
| Sigma Software | Sigma | Swift | UA | 1700 | Outsourcing | yes | no | tier3 | 57 | rem | med | med | high | DOU #14 |
| SoftServe | — | Swift | UA | 7120 | Outsourcing | yes | no | legacy | 69 | rem | high | high | high | DOU #2 |
| Softjourn | — | Swift | UA/US | unk | Outsourcing | yes | no | tier3 | 40 | rem | low | med | low | |
| Solvd | — | Swift Ashby | UA/US | unk | Outsourcing | yes | no | tier3 | 40 | rem | med | high | low | QA iOS noise |
| Sombra | — | Swift HTML | UA | unk | Outsourcing | yes | no | tier3 | 31 | rem | low | low | low | |
| SupportYourApp | — | Py Workable | UA | unk | Support/BPO | yes | no | python | 22 | rem | low | low | low | |
| Vakoms | — | Swift HTML | UA | unk | Outsourcing | yes | no | tier3 | 28 | rem | low | low | low | |
| Xenoss | — | Swift HTML | UA | unk | Outsourcing | yes | no | tier3 | 29 | rem | low | low | low | |
| Yalantis | — | Swift | UA | unk | Outsourcing | yes | no | tier2 | 49 | rem | low | med | low | |
| Zfort | — | Swift HTML | UA | unk | Outsourcing | yes | no | tier3 | 26 | rem | low | low | low | Fragile parser |
| Uklon | — | DOU only | UA | 812 | Product | discovery | no | dou | 53 | hybrid | low | low | low | No dedicated scraper |
| ZONE3000 | — | DOU only | UA | 2205 | Outsourcing/Support | discovery | no | dou | 37 | rem | low | med | low | DOU #8 |

---

## Not in hunters but required by audit checklist

| Name | Status |
|------|--------|
| Luxoft / DXC Luxoft | Missing dedicated source (DOU slug only) |
| Boosta, FRACTAL, Brights, DOIT, Adaptiq | Missing |
| Creatio, Wix, Snap, GitLab, Amazon | Missing |
| Petcube, Jooble | Missing |
| MacPaw, Ajax, Grammarly, Readdle, Preply, Genesis, SKELAR | Present (quality varies) |
| NIX (Kharkiv) | **Not tracked**; distinct from N-iX; appears in Profile interview pipeline |

---

## Recommendations

1. **[Recommendation]** Replace this reconstructed table with a versioned `companies.yaml`.
2. **[Recommendation]** Add explicit `aliases: [N-iX, NiX]` and a separate `NIX` entity to prevent merge errors.
3. **[Recommendation]** Mark Python-only product firms (`Readdle`, `Preply`) as `collect_risk: high`.
