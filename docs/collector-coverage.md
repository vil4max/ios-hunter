# Collector coverage

## Sources

| Layer | What |
|-------|------|
| Python `collector/companies.py` | Orchestrates all company/ATS collectors in parallel |
| Python `collector/generic.py` | Shared HTML helpers (WP REST, HTML regex, BeautifulSoup links) |
| Python `collector/bespoke.py` | Custom career APIs (Andersen, Ciklum, Sigma, DataArt, Grid Dynamics, RBI, …) |
| Python `collector/epam.py` | EPAM sitemap discovery + vacancy `__NEXT_DATA__` (location + remote) |
| Python `collector/dou.py` | DOU iOS/macOS category RSS + per-company vacancy feeds |
| Python `collector/dou_catalog.py` | Periodic DOU companies catalog → `database/dou_companies.json` seed |
| Python `collector/telegram_channels.py` | Telegram chats (MTProto / Telethon): `@itrecruit_ua`, `@remotejobss`, `@itfreelancers`, `@mobile_jobs` |

Retired: **JetSoftPro** (DNS dead); SaaS ATS boards (**Greenhouse**, **Ashby**, **Lever**, **Teamtailor**, **Workable**, **SmartRecruiters**, **Breezy**, **Recruitee**); product/hardware/gaming/bank/telecom careers (Ajax, Samsung, Preply, Genesis, MacPaw, Kyivstar.Tech, Playrix, …); and the small HTML boutique tail. Registry is company career sites of large UA/international **service / outsourcing** shops from the DOU Top-50, plus Djinni, DOU iOS RSS, and Telegram. Former ATS companies stay via their DOU vacancy feeds. Swift collector removed (migrated to Python).

## Location policy

`parser.normalize.is_relevant_job_location` keeps Ukraine (any workplace type) and global remote labels (`Worldwide` / `Anywhere` / `EMEA` / `Europe`). Concrete non-UA geographies (LATAM, USA, Poland, Hungary, …) are dropped. Empty location falls back to title + description; if those also lack a geo signal the vacancy is kept.

## Privacy

New Sync creates **private Project drafts** only. Do not convert drafts to Issues in the public repo.
