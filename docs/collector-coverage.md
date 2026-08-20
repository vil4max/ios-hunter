# Collector coverage

## Sources

| Layer | What |
|-------|------|
| Python `collector/companies.py` | Orchestrates all company/ATS collectors in parallel |
| Python `collector/generic.py` | Shared HTML helpers (WP REST, HTML regex, BeautifulSoup links) |
| Python `collector/bespoke.py` | Custom career APIs (Andersen, Ciklum, Sigma, DataArt, Grid Dynamics, RBI, …) |
| Python `collector/epam.py` | EPAM sitemap discovery + vacancy `__NEXT_DATA__` (location + remote) |
| Python `collector/company_watchlist.py` | Generic official-page monitor and explicit unresolved-source failures |
| Python `collector/dou_service_ratings.py` | Research-only DOU service-company rating → `database/dou_service_companies.json` watchlist |
| Python `collector/dou_top50.py` | Research-only DOU Top 50 discovery; adds companies only when an official career URL is verified |
| Python `collector/dou_catalog.py` | Research-only DOU companies catalog → `database/dou_companies.json` |
| Python `collector/telegram_channels.py` | Telegram chats (MTProto / Telethon): `@itrecruit_ua`, `@remotejobss`, `@itfreelancers`, `@mobile_jobs` |

The production registry contains official career sites and ATS endpoints of large Ukrainian or Ukraine-active **service / outsourcing** companies. Djinni and DOU vacancy feeds are intentionally excluded because they are covered by user subscriptions. DOU is research input for the company watchlist only. Telegram remains supplementary and does not count as official company coverage.

The watchlist is coverage-first: service-rating companies with 200+ specialists form the baseline, and Top 50 companies are added only after their official career URL is verified. Verified URL overrides live in `database/company_career_overrides.json`; explicitly retained companies outside the current DOU snapshots live in `database/company_manual_additions.json`, so every production collector remains visible and can be disabled. Company metadata stays deliberately small: overall DOU rating, compensation rating, survey count, and enabled state. Collector crashes are visible failures; repeated zero-scan pages become degraded rather than being treated as trustworthy empty results.

## Match policy

Location and product domain are metadata, not hard exclusions. The hard filter keeps explicit Apple-platform signals and rejects only high-confidence non-target titles such as QA/test automation/TPM and junior-only roles.

## Privacy

New Sync creates **private Project drafts** only. Do not convert drafts to Issues in the public repo.
