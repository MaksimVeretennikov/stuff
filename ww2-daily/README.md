# WW2 Daily — «Дневник Второй Мировой»

Ежедневная автопубликация о событиях Второй мировой войны «ровно 85 лет назад в этот
день» в Telegram [@ww2_dnevnik](https://t.me/ww2_dnevnik) и в X. Перенос процесса с
make.com на **облачную рутину Claude** (Opus 4.8), работающую без участия компьютера.

## Как это устроено

Творческую работу (текст поста, выбор кадра и подпись) делает **Claude в рамках
ежедневной рутины** на подписке MAX — отдельный платный Anthropic API не нужен.
Детерминированную «инфраструктуру» делают скрипты этого репозитория:

| Этап | Скрипт | Что делает |
|------|--------|------------|
| 1. Факты | `python -m ww2daily.fetch_sources` | Собирает день из onwar, RU «Хроника ВОВ», EN таймлайна, ww2db + контекст прошлых постов → `build/daily_brief.json` |
| 2. Текст | *(Claude)* | По `prompts/post.md` пишет `post_tg`, `post_x`, запросы для фото |
| 3. Фото | `python -m ww2daily.find_photos "<image_query>" "<category_query>"` | Ищет кадры на Wikimedia Commons, **отсекает уже использованные** (по `pageId`) и послевоенные → `build/photo_candidates.json` |
| 4. Выбор | *(Claude)* | Смотрит кадры, выбирает подходящий, пишет подпись → `build/chosen.json` |
| 5. Публикация | `python -m ww2daily.publish` | Telegram (фото+подпись) + X через Buffer, обновляет `state/history.json` |

Антиповтор тем и фото держится в `state/history.json` (память между днями).

## Структура

```
ww2daily/        пакет: config, dates, text, http, fetch_sources, find_photos, publish
prompts/post.md  промпт генерации (правила поста, фото, подписи)
state/history.json  история постов + использованные pageId (антиповтор)
tests/           офлайн-тесты логики (без сети)
ROUTINE.md       текст рутины + как её создать в Claude
```

## Настройка (делается один раз)

### 1. Переменные окружения (секреты)

> ⚠️ **Не вставляй токены в чат.** Добавь их как переменные окружения среды Claude
> (claude.ai/code → нужная среда → **Settings → Environment variables**). Скрипты читают
> их через `os.environ` и **никогда не печатают** в логи. Так токены не попадают в
> переписку.

| Переменная | Зачем | Обязательна |
|------------|-------|-------------|
| `TELEGRAM_BOT_TOKEN` | публикация в Telegram (бот должен быть **админом** канала) | да |
| `BUFFER_ACCESS_TOKEN` | публикация в X через Buffer | да (фаза 1) |
| `BUFFER_PROFILE_ID` | id канала X в Buffer (по умолчанию уже зашит из make.com) | нет |
| `AIRTABLE_PAT` | разовая миграция истории/`pageId` из Airtable | желательно |

### 2. Сетевая политика

Среда по умолчанию (**Trusted**) блокирует внешние домены. Переключи на **Custom** и
добавь в allowlist (плюс «common package managers» для pip):

```
api.telegram.org
api.bufferapp.com
api.airtable.com
commons.wikimedia.org
upload.wikimedia.org
ru.wikipedia.org
en.wikipedia.org
ww2db.com
www.onwar.com
```

### 3. Зависимости

Setup-скрипт среды: `pip install -r requirements.txt`.

## Локальная проверка

```bash
python -m tests.test_offline                 # логика без сети
python -m ww2daily.fetch_sources             # нужен доступ к сети
python -m ww2daily.find_photos "Narvik battle 1940" "Battle of Narvik"
python -m ww2daily.publish --dry-run         # проверить длины, ничего не публикуя
```

## Миграция истории из Airtable (рекомендуется до первого запуска)

Чтобы фото не повторялись с уже опубликованными и у модели был контекст, засей
`state/history.json` из текущей таблицы Airtable
(`base appLeMglWrKtgCBh7 / table tblyF452mZzF1sCq1`): перенеси прошлые посты в
`posts[]` и все использованные `pageId` в `used_page_ids[]`. Скрипт миграции добавлю
после получения `AIRTABLE_PAT`.

## Лимиты длины (зашиты в `ww2daily/config.py`)

- Telegram: подпись `<i>фото</i>` + пост ≤ **1024** (UTF-16). Пост целится в 820–900.
- X: ≤ **280** (URL = 23, emoji/CJK = 2). `publish.py` проверяет и не даёт превысить.

## Дорожная карта

1. ✅ Ежедневный пост (этот репозиторий).
2. ⏳ Опросы (перенос из Airtable).
3. ⏳ Доп. рубрики.
4. ⏳ Опционально: прямой X API вместо Buffer (см. ROUTINE.md → заметка про X).
