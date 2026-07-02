# iOS Hunter

Поисковик iOS/Swift вакансий на украинском рынке. Работает **только на GitHub Actions** — локально ничего запускать не нужно.

Каждый рабочий час бот обходит карьерные страницы компаний, сравнивает с прошлым состоянием и **присылает в Telegram новые и изменённые вакансии**, которые подходят под твой профиль.

DOU и Djinni здесь **не собираются** — ты смотришь их в приложениях на iPhone.

---

## Что делает сейчас

### 1. Сбор вакансий
- **~52 карьерных страницы** компаний (Swift-коллектор)
- Дополнительно JSON-фиды Teamtailor (Levi9, Avenga)
- Фильтр по заголовку: iOS / Swift

### 2. Отслеживание изменений
Для каждой вакансии хранится история. На каждом прогоне определяется:

| Событие | Что значит |
|---------|------------|
| **New** | Вакансия появилась впервые |
| **Updated** | Изменилось описание или заголовок |
| **Reopened** | Закрытая вакансия снова открылась |
| **Closed** | Вакансии больше нет на сайте компании |

### 3. Уведомления в Telegram
На **actionable** события (New + Updated + Reopened) с match score ≥ 60 приходит **application pack**:

- компания, должность, ссылка
- match score, Strong / Gap
- черновик cover letter
- portfolio и CV: [vil4max.github.io](https://vil4max.github.io)

Зарплата из текста вакансии показывается **информативно**, если найдена. **Фильтра по ЗП нет** — решение за тобой.

### 4. Company Watch
Если у компании **3+ открытых mobile/iOS ролей** — отдельный алерт в Telegram (не чаще 1 раза в неделю на компанию).

### 5. Отчёты и публичные данные
После каждого прогона в репозиторий коммитятся:

- `reports/activity/` — что изменилось за run
- `reports/health/` — состояние источников
- `reports/market/`, `reports/timeline/` — снимок рынка
- `reports/weekly/` — недельный отчёт
- `website/` — дашборд и RSS для GitHub Pages

База `database/jobs.db` хранится в cache Actions и **не коммитится**.

### 6. CRM (опционально)
Трекинг откликов и follow-up напоминания — CLI в репозитории, если понадобится вручную.

---

## Расписание (GitHub Actions)

| Workflow | Когда |
|----------|-------|
| **Collect iOS Jobs** | Каждый час, **пн–пт 08:00–18:00 по Киеву** |
| **Weekly iOS Market Report** | Понедельник 09:00 Киев |
| **AI Analysis** | Понедельник 09:30 (только если задан `OPENAI_API_KEY` или `GEMINI_API_KEY`) |

Ручной запуск: **Actions → Collect iOS Jobs → Run workflow**.

---

## Как это устроено

```
GitHub Actions (macOS + Ubuntu)
        │
   Swift — собирает вакансии с career pages
        │ swift_export.json
   Python — дедуп, diff, база, Telegram, отчёты
        │
   database/jobs.db (cache)  →  Telegram тебе
        │
   auto-commit reports + website → main
```

Стек: Swift 6 · Python 3.12 · SQLite · Telegram Bot API · GitHub Pages

---

## Настройка (один раз)

Кратко:

1. Secrets: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
2. Enable Actions + GitHub Pages
3. Отредактировать `config/profile.yaml` — имя, portfolio, ссылки на CV

---

## Документация

- [ARCHITECTURE.md](ARCHITECTURE.md) — архитектура
- [ROADMAP.md](ROADMAP.md) — планы развития
