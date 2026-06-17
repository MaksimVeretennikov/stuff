"""Поиск кандидатов-фотографий на Wikimedia Commons + антиповтор.

Запуск:  python -m ww2daily.find_photos "<image_query>" "<category_query>"
Результат: build/photo_candidates.json — список кадров, из которых Claude в рутине
выбирает лучший (визуально) и пишет подпись.

Логика портирована из текущего сценария make.com (поиск по файлам + по категориям,
дедуп по использованным pageId, отсечение по году съёмки)."""

from __future__ import annotations

import json
import os
import re
import sys

from bs4 import BeautifulSoup

from . import config, http

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
MAX_CANDIDATES = 8


def _clean(text: str | None, max_len: int = 220) -> str | None:
    if not text:
        return None
    s = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    s = " ".join(s.split())
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0]
    return s or None


def _first_year(text: str | None) -> int | None:
    if not text:
        return None
    m = re.search(r"\d{4}", str(text))
    return int(m.group(0)) if m else None


def _imageinfo(page: dict) -> dict:
    ii = page.get("imageinfo") or [{}]
    return ii[0] if ii else {}


def _orig_year(page: dict) -> int | None:
    meta = _imageinfo(page).get("extmetadata", {})
    return _first_year((meta.get("DateTimeOriginal") or {}).get("value"))


def search_files(image_query: str) -> dict:
    """ns=6, поиск файлов-картинок по запросу (как gsrsearch в make.com)."""
    if not image_query:
        return {}
    params = {
        "action": "query", "generator": "search", "gsrnamespace": 6,
        "gsrlimit": 20, "gsrsearch": f"filetype:bitmap {image_query}",
        "prop": "imageinfo", "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 1200, "format": "json",
    }
    try:
        return http.get_json(COMMONS_API, params=params).get("query", {}).get("pages", {})
    except Exception:
        return {}


def search_category_files(category_query: str) -> dict:
    """ns=14: найти категорию по запросу, затем её файлы (как в make.com)."""
    if not category_query:
        return {}
    try:
        cats = http.get_json(COMMONS_API, params={
            "action": "query", "list": "search", "srnamespace": 14,
            "srsearch": category_query, "srlimit": 3, "format": "json",
        }).get("query", {}).get("search", [])
    except Exception:
        return {}
    pages: dict = {}
    for c in cats:
        title = c.get("title")
        if not title:
            continue
        try:
            members = http.get_json(COMMONS_API, params={
                "action": "query", "generator": "categorymembers",
                "gcmtitle": title, "gcmtype": "file", "gcmlimit": 15,
                "prop": "imageinfo", "iiprop": "url|mime|extmetadata",
                "iiurlwidth": 1200, "format": "json",
            }).get("query", {}).get("pages", {})
            pages.update(members)
        except Exception:
            continue
    return pages


def build_candidates(image_query: str, category_query: str) -> list[dict]:
    used = set()
    if os.path.exists(config.HISTORY_PATH):
        with open(config.HISTORY_PATH, encoding="utf-8") as f:
            used = {str(x) for x in json.load(f).get("used_page_ids", [])}

    pages = {}
    pages.update(search_files(image_query))
    pages.update(search_category_files(category_query))

    out = []
    seen = set()
    for page in pages.values():
        pid = str(page.get("pageid"))
        if pid in used or pid in seen:
            continue
        year = _orig_year(page)
        if year is not None and year > 1950:  # отсекаем послевоенные/современные кадры
            continue
        ii = _imageinfo(page)
        url = ii.get("thumburl") or ii.get("url")
        if not url:
            continue
        desc = _clean((ii.get("extmetadata", {}).get("ImageDescription") or {}).get("value"))
        seen.add(pid)
        out.append({
            "pageid": page.get("pageid"),
            "title": page.get("title"),
            "url": url,
            "description": desc,
            "year": year,
        })
        if len(out) >= MAX_CANDIDATES:
            break
    return out


def main(argv: list[str]) -> None:
    image_query = argv[0] if len(argv) > 0 else ""
    category_query = argv[1] if len(argv) > 1 else ""
    os.makedirs(config.BUILD_DIR, exist_ok=True)
    candidates = build_candidates(image_query, category_query)
    with open(config.PHOTO_CANDIDATES_PATH, "w", encoding="utf-8") as f:
        json.dump({"image_query": image_query, "category_query": category_query,
                   "candidates": candidates}, f, ensure_ascii=False, indent=2)
    print(f"Найдено кандидатов (после дедупа/фильтра): {len(candidates)}")
    for i, c in enumerate(candidates, 1):
        print(f"  {i}. [{c['year']}] {c['title']}  ->  {c['url']}")
        if c["description"]:
            print(f"     {c['description']}")
    print(f"Сохранено: {config.PHOTO_CANDIDATES_PATH}")


if __name__ == "__main__":
    main(sys.argv[1:])
