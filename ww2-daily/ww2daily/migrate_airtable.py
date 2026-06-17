"""Разовая миграция истории из Airtable в state/history.json.

Главная цель — восстановить список **использованных pageId** (чтобы фото не повторялись
с уже опубликованными) и темы прошлых постов для контекста.

Запуск:
  AIRTABLE_PAT=... python -m ww2daily.migrate_airtable --dry-run
  AIRTABLE_PAT=... python -m ww2daily.migrate_airtable          # записать в history.json
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

from . import config, http
from .dates import subtract_years


def _norm_pageid(v):
    if v is None:
        return None
    s = str(v).strip()
    return int(s) if s.isdigit() else (s or None)


def record_to_post(fields: dict) -> dict:
    """fields — поля записи Airtable (по ID полей). Чистая функция (тестируется офлайн)."""
    date_today_str = fields.get(config.AIRTABLE_FIELD_DATE)
    post_x = (fields.get(config.AIRTABLE_FIELD_POST_X) or "").strip()
    caption = (fields.get(config.AIRTABLE_FIELD_CAPTION) or "").strip()
    pageid = _norm_pageid(fields.get(config.AIRTABLE_FIELD_PAGEID))

    date_ww2 = None
    sort_key = date_today_str or ""
    if date_today_str:
        try:
            d = _dt.datetime.strptime(date_today_str.strip(), "%d.%m.%Y").date()
            date_ww2 = subtract_years(d, config.YEARS_BACK).strftime("%d.%m.%Y")
            sort_key = d.isoformat()
        except ValueError:
            pass
    return {
        "date_ww2": date_ww2,
        "title": (caption or post_x)[:80],
        "post_x": post_x,
        "photo_caption": caption,
        "image_pageid": pageid,
        "_sort": sort_key,
    }


def fetch_records(pat: str) -> list[dict]:
    url = f"https://api.airtable.com/v0/{config.AIRTABLE_BASE}/{config.AIRTABLE_TABLE}"
    headers = {"Authorization": f"Bearer {pat}"}
    records, offset = [], None
    while True:
        params = {"pageSize": 100, "returnFieldsByFieldId": "true"}
        if offset:
            params["offset"] = offset
        data = http.get_json(url, params=params, headers=headers)
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def build_history(records: list[dict]) -> dict:
    posts = [record_to_post(r.get("fields", {})) for r in records]
    posts.sort(key=lambda p: p.pop("_sort"))  # хронологически: старые -> новые
    used = []
    seen = set()
    for p in posts:
        pid = p.get("image_pageid")
        if pid is not None and str(pid) not in seen:
            seen.add(str(pid))
            used.append(pid)
    return {"posts": posts, "used_page_ids": used}


def main(argv: list[str]) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=config.HISTORY_PATH)
    args = ap.parse_args(argv)

    pat = os.environ.get("AIRTABLE_PAT")
    if not pat:
        sys.exit("ОШИБКА: не задана переменная окружения AIRTABLE_PAT")

    records = fetch_records(pat)
    hist = build_history(records)
    print(f"Записей в Airtable: {len(records)}")
    print(f"Постов в историю: {len(hist['posts'])}")
    print(f"Уникальных pageId (антиповтор фото): {len(hist['used_page_ids'])}")
    if args.dry_run:
        print("DRY RUN — файл не записан. Примеры последних тем:")
        for p in hist["posts"][-5:]:
            print(f"  {p['date_ww2']}: {p['title']}")
        return
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)
    print(f"Записано: {args.out}")


if __name__ == "__main__":
    main(sys.argv[1:])
