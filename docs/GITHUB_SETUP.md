# Настройка GitHub для iOS Hunter

Пошаговая инструкция — что сделать **один раз** после merge PR.

---

## Шаг 1. Смержить PR

1. Открой PR: https://github.com/vil4max/ios-hunter/pull/6
2. Нажми **Merge pull request**
3. Убедись, что ветка `main` содержит workflows и Python-код

Без merge workflows на `main` не запустятся по расписанию.

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

## Шаг 3. GitHub Actions (автозапуск)

1. Репозиторий → вкладка **Actions**
2. Если видишь «Workflows disabled» — нажми **Enable Actions**
3. Workflow **Collect iOS Jobs** запускается:
   - **каждый час** автоматически
   - вручную: Actions → Collect iOS Jobs → **Run workflow**

### Что делает collect.yml

```
Swift collector → Python pipeline → Telegram → commit reports → push в main
```

После каждого успешного запуска в репозиторий коммитятся:

- `reports/` — activity, health, market, timeline, weekly
- `website/data/` — JSON для дашборда
- `website/feed.xml` — RSS
- `database/jobs.json` — открытые вакансии

SQLite (`jobs.db`) **не** коммитится — хранится в cache Actions.

---

## Шаг 4. GitHub Pages (публичный дашборд)

Нужен, если хочешь публичную страницу со статистикой рынка.

1. Репозиторий → **Settings** → **Pages**
2. **Build and deployment** → Source: **GitHub Actions**
3. Сохрани

После первого push в `main` с обновлёнными `website/` файлами:

1. Actions → **Deploy GitHub Pages** — должен отработать автоматически
2. Сайт будет по адресу:
   ```
   https://vil4max.github.io/ios-hunter/
   ```

Если deploy не стартует — Actions → Deploy GitHub Pages → **Run workflow** вручную.

---

## Шаг 5. config/profile.yaml (в репозитории)

Отредактируй в `main` (или до merge):

```yaml
name: "Твоё Имя"
portfolio_url: "https://твой-сайт.com"
cv_urls:
  fintech: "https://..."
  ai: "https://..."
  sdk: "https://..."
  product: "https://..."
```

Это подставляется в cover letter и Telegram pack.

---

## Чеклист

| # | Что | Где | Обязательно? |
|---|-----|-----|--------------|
| 1 | Merge PR | GitHub Pull Requests | Да |
| 2 | `TELEGRAM_TOKEN` | Settings → Secrets | Для уведомлений |
| 3 | `TELEGRAM_CHAT_ID` | Settings → Secrets | Для уведомлений |
| 4 | Enable Actions | Actions tab | Да |
| 5 | Pages → GitHub Actions | Settings → Pages | Для публичного сайта |
| 6 | `config/profile.yaml` | В коде репо | Для CV/portfolio ссылок |

---

## Частые вопросы

**Нужен ли свой сервер?**  
Нет. Всё на GitHub Actions + Pages бесплатно.

**Почему нет уведомлений?**  
Проверь secrets и что match score ≥ 60 и зарплата ≥ $4500 (если указана в вакансии).

**Где смотреть логи?**  
Actions → Collect iOS Jobs → последний run → шаги «Run Swift collector» / «Run Python pipeline».

**Как запустить вручную?**  
Actions → Collect iOS Jobs → Run workflow.
