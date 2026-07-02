# Настройка GitHub для iOS Hunter

Пошаговая инструкция — что проверить **один раз**, чтобы всё работало на GitHub.

> **Статус (2026-07-02):** код и workflows уже в `main`, Collect iOS Jobs запускается по расписанию.  
> **GitHub Pages ещё не включён** — публичный дашборд по адресу https://vil4max.github.io/ios-hunter/ возвращает 404.

---

## Шаг 1. GitHub Actions

1. Репозиторий → вкладка **Actions**
2. Если видишь «Workflows disabled» — нажми **Enable Actions**
3. Workflow **Collect iOS Jobs** запускается:
   - **каждый час в рабочее время** (пн–пт, 08:00–18:00 по Киеву)
   - вручную: Actions → Collect iOS Jobs → **Run workflow**

### Что делает collect.yml

```
Swift collector → swift_export.json → Python pipeline → jobs.db → Telegram → commit reports
```

Одна база данных: **`database/jobs.db`** (хранится в cache Actions, не коммитится).

После каждого успешного запуска в репозиторий коммитятся:

- `reports/` — activity, health, market, timeline, weekly, companies
- `website/data/` — JSON для дашборда
- `website/feed.xml` — RSS
- `database/jobs.json`, `database/history.json` — открытые вакансии и история

---

## Шаг 2. Telegram (для уведомлений)

Нужно, чтобы бот присылал application packs в личку.

### 2.1 Создать бота

1. В Telegram найди [@BotFather](https://t.me/BotFather)
2. Отправь `/newbot`
3. Следуй инструкциям → получишь **токен** вида `123456789:ABCdef...`

### 2.2 Узнать Chat ID

1. Напиши своему боту любое сообщение (например `hi`)
2. Открой в браузере:
   ```
   https://api.telegram.org/bot<ТВОЙ_ТОКЕН>/getUpdates
   ```
3. Найди `"chat":{"id": 123456789` — это **Chat ID**

### 2.3 Добавить Secrets в GitHub

1. Репозиторий → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**:
   - Name: `TELEGRAM_TOKEN` → Value: токен бота
   - Name: `TELEGRAM_CHAT_ID` → Value: твой chat id

> Если secrets не заданы — pipeline всё равно работает, но уведомления печатаются только в лог CI.

---

## Шаг 3. GitHub Pages (публичный дашборд)

**Сейчас не настроено.** Workflow `Deploy GitHub Pages` падает с `HttpError: Not Found`, пока Pages не включён в настройках репозитория.

### Чеклист включения Pages

| # | Действие | Где | Проверка |
|---|----------|-----|----------|
| 1 | Открыть настройки Pages | [Settings → Pages](https://github.com/vil4max/ios-hunter/settings/pages) | Страница открывается |
| 2 | Source: **GitHub Actions** | Build and deployment → Source | Не «Deploy from a branch» |
| 3 | Сохранить | — | В Settings → Pages нет предупреждения |
| 4 | Запустить deploy вручную | Actions → **Deploy GitHub Pages** → Run workflow | Run завершился success |
| 5 | Проверить сайт | https://vil4max.github.io/ios-hunter/ | HTTP 200, не 404 |

### После включения

1. Actions → **Deploy GitHub Pages** — отработает автоматически при push в `main` с обновлёнными `website/` файлами
2. Сайт будет по адресу:
   ```
   https://vil4max.github.io/ios-hunter/
   ```

Если deploy не стартует — Actions → Deploy GitHub Pages → **Run workflow** вручную.

---

## Шаг 4. config/profile.yaml

Профиль уже настроен в `main`. При необходимости отредактируй:

```yaml
name: "Max Vilchevskiy"
portfolio_url: "https://vil4max.github.io"
cv_urls:
  default: "https://vil4max.github.io"
  ai: "https://vil4max.github.io"
  sdk: "https://vil4max.github.io"
  product: "https://vil4max.github.io"

cover_letter:
  include_salary: false

match_threshold: 60
```

Это подставляется в cover letter и Telegram pack. **Фильтра по зарплате нет** — зарплата из вакансии показывается только информативно.

---

## Чеклист

| # | Что | Где | Статус |
|---|-----|-----|--------|
| 1 | Enable Actions | Actions tab | ✅ работает |
| 2 | Collect iOS Jobs по расписанию | Actions → Collect iOS Jobs | ✅ success |
| 3 | `TELEGRAM_TOKEN` | Settings → Secrets | ⚠️ проверь вручную |
| 4 | `TELEGRAM_CHAT_ID` | Settings → Secrets | ⚠️ проверь вручную |
| 5 | Pages → GitHub Actions | Settings → Pages | ❌ не включено |
| 6 | `config/profile.yaml` | В коде репо | ✅ настроен |

---

## Частые вопросы

**Нужен ли свой сервер?**  
Нет. Всё на GitHub Actions + Pages бесплатно.

**Почему нет уведомлений?**  
Проверь `TELEGRAM_TOKEN` и `TELEGRAM_CHAT_ID`. Уведомления приходят только для actionable событий (New / Updated / Reopened) с **match score ≥ 60**. Фильтра по зарплате нет.

**Почему сайт 404?**  
GitHub Pages не включён. См. [Шаг 3](#шаг-3-github-pages-публичный-дашборд).

**Где смотреть логи?**  
Actions → Collect iOS Jobs → последний run → шаги «Run Swift collector» / «Run Python pipeline».

**Как запустить вручную?**  
Actions → Collect iOS Jobs → Run workflow.
