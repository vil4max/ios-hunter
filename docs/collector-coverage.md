# Collector coverage

## Sources

| Layer | What |
|-------|------|
| Swift `JobSources.all` | Manual career-page / ATS adapters (company list in `JobSource.swift`) |
| Python `collector/companies.py` | Extra ATS boards (Greenhouse, Ashby, Lever, Workable, Teamtailor, …) |
| Python `collector/dou.py` | DOU Top 50 career discovery + iOS/Swift feeds |
| Python `collector/telegram_channels.py` | Telegram chats (MTProto / Telethon); currently `@itrecruit_ua` |

Retired: **JetSoftPro** (DNS dead; removed from Swift registry).

## Privacy

New Sync creates **private Project drafts** only. Do not convert drafts to Issues in the public repo.
