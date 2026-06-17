"""Несекретная конфигурация проекта.

Секреты (токены) сюда НЕ кладём — они приходят из переменных окружения
(см. ww2daily.publish и README → раздел «Переменные окружения»).
"""

import os

# --- Канал и соцсети ----------------------------------------------------------
TELEGRAM_CHANNEL = "@ww2_dnevnik"

# Buffer: id подключённого канала (профиля) X. Это НЕ organizationId.
# Значение взято из текущего сценария make.com (модуль buffer:ActionCreateStatus).
BUFFER_PROFILE_ID = os.environ.get("BUFFER_PROFILE_ID", "691383278a760604e4bebae5")

# --- Логика даты --------------------------------------------------------------
TIMEZONE = "Europe/Moscow"
YEARS_BACK = 85  # «ровно N лет назад»

# --- Бюджеты длины ------------------------------------------------------------
# Telegram: фото + подпись одним сообщением. Жёсткий лимит подписи — 1024
# UTF-16 code units. Подпись = "<i>{подпись к фото}</i>\n\n{пост}".
# Поэтому держим запас: сам пост до ~900, подпись к фото до ~120, суммарно <= 1000.
TG_CAPTION_HARD_LIMIT = 1024      # лимит Telegram (UTF-16 code units)
TG_CAPTION_TARGET = 1000          # с запасом
POST_TG_MAX = 900                 # «пост до тысячи знаков» — целимся в 820–900
PHOTO_CAPTION_MAX = 120           # подпись к фото (курсив, первая строка)

# X (Twitter): стандартный лимит 280 (взвешенный: URL = 23, emoji/CJK = 2).
X_MAX = 280

# --- Контекст истории для модели ---------------------------------------------
# Сколько прошлых постов отдавать модели, чтобы не повторять темы и фото.
# Полный текст последних N + краткие «темы» последних M (компромисс размер/память).
HISTORY_FULL = 5     # полный текст последних 5 постов
HISTORY_BRIEF = 30   # темы/заголовки последних 30 постов

# --- Источники фактуры --------------------------------------------------------
# Каждый источник best-effort: падение одного не ломает день.
WIKIMEDIA_UA = (
    "ww2-daily-bot/0.1 (https://t.me/ww2_dnevnik; maksim.veretennik@gmail.com)"
)

# RU «Хроника Великой Отечественной войны (<месяц> <год> года)» — по дням,
# но только с 22.06.1941 (для более ранних дат СССР-источник пуст — это норма).
RU_CHRONICLE_TEMPLATE = "Хроника Великой Отечественной войны ({month_nom} {year} года)"
# EN «Timeline of World War II (<год>)» — глобальный контекст по дням.
EN_TIMELINE_TEMPLATE = "Timeline of World War II ({year})"

# onwar: помесячная хроника (проверенный парсер из make.com).
ONWAR_URL_TEMPLATE = "https://www.onwar.com/wwii/chronology/{yyyymm}.html"
# ww2db: «в этот день» по всем военным годам.
WW2DB_URL_TEMPLATE = "https://ww2db.com/event/today/{mm}/{dd}/{year}"

# --- Файлы --------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(ROOT, "state", "history.json")
BUILD_DIR = os.path.join(ROOT, "build")
DAILY_BRIEF_PATH = os.path.join(BUILD_DIR, "daily_brief.json")
PHOTO_CANDIDATES_PATH = os.path.join(BUILD_DIR, "photo_candidates.json")
PROMPT_PATH = os.path.join(ROOT, "prompts", "post.md")
