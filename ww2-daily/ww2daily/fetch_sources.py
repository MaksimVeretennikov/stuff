"""Сбор фактуры из нескольких источников + контекст прошлых постов.

Запуск:  python -m ww2daily.fetch_sources
Результат: build/daily_brief.json — его читает Claude в рутине и пишет пост.

Каждый источник best-effort: падение одного не ломает день.
"""

from __future__ import annotations

import json
import os
import re

from bs4 import BeautifulSoup

from . import config, http
from .dates import TargetDate

# --- Парсеры (вынесены, чтобы юнит-тестить офлайн) ----------------------------


def parse_onwar(html: str, header: str) -> str:
    """Блок одного дня со страницы помесячной хроники onwar.com.

    Проверенная логика из текущего сценария make.com: ищем <h2>{дата}</h2>,
    берём все <p> до <hr>/</body>/</html>, чистим теги, склеиваем.
    """
    if not html or not header:
        return ""
    m = re.search(
        r"(?is)<h2>\s*" + re.escape(header) + r"\s*</h2>(.*?)(?:<hr>|</body>|</html>)",
        html,
    )
    if not m:
        return ""
    paragraphs = re.findall(r"(?is)<p>(.*?)</p>", m.group(1))
    cleaned = []
    for p in paragraphs:
        txt = BeautifulSoup(p, "html.parser").get_text(" ", strip=True)
        txt = " ".join(txt.split())
        if txt:
            cleaned.append(txt)
    return "\n\n".join(cleaned)


def extract_day_lines(plain_text: str, markers: list[str], max_chars: int = 4000) -> str:
    """Из «плоского» текста статьи выбрать абзацы/строки, упоминающие нужный день.

    Грубо, но Claude в рутине дочитает контекст. markers, напр.: ['17 июня'] или
    ['June 17', '17 June'].
    """
    if not plain_text:
        return ""
    lines = [ln.strip() for ln in re.split(r"[\n\r]+", plain_text) if ln.strip()]
    hits = []
    for ln in lines:
        if any(mk.lower() in ln.lower() for mk in markers):
            hits.append(ln)
    out = "\n".join(hits)
    return out[:max_chars]


def _wiki_plain(api_base: str, page: str) -> str | None:
    """Рендер статьи (action=parse, prop=text) -> чистый текст."""
    html = http.mediawiki_parse(api_base, page, prop="text")
    if not html:
        return None
    return BeautifulSoup(html, "html.parser").get_text("\n", strip=True)


# --- Источники ----------------------------------------------------------------


def source_onwar(td: TargetDate) -> str:
    url = config.ONWAR_URL_TEMPLATE.format(yyyymm=td.yyyymm)
    try:
        html = http.get(url).text
    except Exception:
        return ""
    return parse_onwar(html, td.onwar_header)


def source_ru_chronicle(td: TargetDate) -> str:
    """RU «Хроника ВОВ (<месяц> <год> года)» — только с 22.06.1941; раньше пусто (норма)."""
    if (td.year, td.month, td.day) < (1941, 6, 22):
        return ""
    page = config.RU_CHRONICLE_TEMPLATE.format(month_nom=td.ru_month_nom, year=td.year)
    plain = _wiki_plain("https://ru.wikipedia.org", page)
    if not plain:
        return ""
    from .dates import RU_MONTHS_GEN
    marker = f"{td.day} {RU_MONTHS_GEN[td.month]}"  # «17 июня»
    return extract_day_lines(plain, [marker])


def source_en_timeline(td: TargetDate) -> str:
    page = config.EN_TIMELINE_TEMPLATE.format(year=td.year)
    plain = _wiki_plain("https://en.wikipedia.org", page)
    if not plain:
        return ""
    from .dates import EN_MONTHS
    mon = EN_MONTHS[td.month]
    return extract_day_lines(plain, [f"{mon} {td.day}", f"{td.day} {mon}"])


def source_ww2db(td: TargetDate) -> str:
    url = config.WW2DB_URL_TEMPLATE.format(mm=td.mm, dd=td.dd, year=td.year)
    try:
        html = http.get(url).text
    except Exception:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    text = re.sub(r"\n{2,}", "\n", text)
    return text[:4000]


# --- Контекст истории ---------------------------------------------------------


def load_history() -> dict:
    if not os.path.exists(config.HISTORY_PATH):
        return {"posts": [], "used_page_ids": []}
    with open(config.HISTORY_PATH, encoding="utf-8") as f:
        return json.load(f)


def history_context(hist: dict) -> dict:
    posts = hist.get("posts", [])
    full = posts[-config.HISTORY_FULL:]
    brief = [
        {"date_ww2": p.get("date_ww2"), "title": p.get("title")}
        for p in posts[-config.HISTORY_BRIEF:]
    ]
    return {"recent_full": full, "recent_titles": brief}


# --- main ---------------------------------------------------------------------


def build_brief() -> dict:
    td = TargetDate()
    hist = load_history()
    sources = {
        "onwar": source_onwar(td),
        "ru_chronicle": source_ru_chronicle(td),
        "en_timeline": source_en_timeline(td),
        "ww2db": source_ww2db(td),
    }
    sources_ok = [k for k, v in sources.items() if v]
    return {
        "date": td.as_dict(),
        "sources": sources,
        "sources_ok": sources_ok,
        "history": history_context(hist),
    }


def main() -> None:
    os.makedirs(config.BUILD_DIR, exist_ok=True)
    brief = build_brief()
    with open(config.DAILY_BRIEF_PATH, "w", encoding="utf-8") as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)
    print(f"Дата: {brief['date']['human_ru']}")
    print(f"Источники с данными: {brief['sources_ok'] or 'НЕТ (проверь сеть/политику)'}")
    for k, v in brief["sources"].items():
        print(f"  - {k}: {len(v)} символов")
    print(f"История: {len(brief['history']['recent_titles'])} прошлых постов в контексте")
    print(f"Сохранено: {config.DAILY_BRIEF_PATH}")


if __name__ == "__main__":
    main()
