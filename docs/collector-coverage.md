# Collector coverage

## Sources

| Layer | What |
|-------|------|
| Python `collector/companies.py` | Orchestrates all company/ATS collectors in parallel |
| Python `collector/generic.py` | Shared ATS/HTML helpers (Ashby, Greenhouse, Workable widget, WP REST, Breezy, HTML regex, BeautifulSoup links) |
| Python `collector/bespoke.py` | Custom career APIs (Andersen, Ciklum, Sigma, DataArt, Grid Dynamics, RBI, …) |
| Python `collector/epam.py` | EPAM sitemap discovery + vacancy `__NEXT_DATA__` (location + remote) |
| Python `collector/dou.py` | DOU Top 50 career discovery + iOS/Swift feeds |
| Python `collector/telegram_channels.py` | Telegram chats (MTProto / Telethon): `@itrecruit_ua`, `@remotejobss`, `@itfreelancers` |

Retired: **JetSoftPro** (DNS dead). Swift collector removed (migrated to Python).

## Location policy

`parser.normalize.is_relevant_job_location` keeps Ukraine (any workplace type) and global remote labels (`Worldwide` / `Anywhere` / `EMEA` / `Europe`). Concrete non-UA geographies (LATAM, USA, Poland, Hungary, …) are dropped. Unknown / empty location is kept.

## Privacy

New Sync creates **private Project drafts** only. Do not convert drafts to Issues in the public repo.
