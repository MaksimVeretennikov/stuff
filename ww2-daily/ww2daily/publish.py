"""Публикация готового поста: Telegram (фото+подпись) + X через Buffer, затем
обновление истории (антиповтор).

Запуск:  python -m ww2daily.publish [--dry-run] [--skip-x] [--skip-tg]
Читает build/chosen.json со структурой:
{
  "title": "<короткая тема дня, для истории>",
  "post_tg": "<пост, теги <b>..</b> допустимы>",
  "post_x": "<англ. пост до 280>",
  "photo_caption": "<подпись к фото, рус., до 120>",
  "image_url": "<публичный URL картинки с Commons>",
  "image_pageid": <pageid с Commons>
}

Секреты — только из окружения, в логи НЕ печатаются:
  TELEGRAM_BOT_TOKEN, BUFFER_ACCESS_TOKEN
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import requests

from . import config, http, text
from .dates import TargetDate

TG_API = "https://api.telegram.org"
BUFFER_API = "https://api.bufferapp.com/1/updates/create.json"


def _load_chosen() -> dict:
    path = os.path.join(config.BUILD_DIR, "chosen.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        sys.exit(f"ОШИБКА: не задана переменная окружения {name}")
    return val


def send_telegram(chosen: dict, caption: str) -> dict:
    token = _require_env("TELEGRAM_BOT_TOKEN")
    img = http.get(chosen["image_url"])  # скачиваем байты (надёжнее, чем photo=URL)
    files = {"photo": ("photo.jpg", img.content)}
    data = {
        "chat_id": config.TELEGRAM_CHANNEL,
        "caption": caption,
        "parse_mode": "HTML",
    }
    r = requests.post(f"{TG_API}/bot{token}/sendPhoto", data=data, files=files, timeout=60)
    r.raise_for_status()
    return r.json()


def send_buffer(chosen: dict) -> dict:
    token = _require_env("BUFFER_ACCESS_TOKEN")
    # Buffer берёт ПУБЛИЧНЫЙ URL картинки (Commons подходит) — Dropbox больше не нужен.
    data = {
        "profile_ids[]": config.BUFFER_PROFILE_ID,
        "text": chosen["post_x"],
        "media[picture]": chosen["image_url"],
        "media[thumbnail]": chosen["image_url"],
        "now": "true",
        "access_token": token,
    }
    r = requests.post(BUFFER_API, data=data, timeout=60)
    r.raise_for_status()
    return r.json()


def update_history(chosen: dict) -> None:
    td = TargetDate()
    if os.path.exists(config.HISTORY_PATH):
        with open(config.HISTORY_PATH, encoding="utf-8") as f:
            hist = json.load(f)
    else:
        hist = {"posts": [], "used_page_ids": []}
    hist.setdefault("posts", []).append({
        "date_today": td.today.isoformat(),
        "date_ww2": td.dotted,
        "title": chosen.get("title", ""),
        "post_tg": chosen.get("post_tg", ""),
        "post_x": chosen.get("post_x", ""),
        "photo_caption": chosen.get("photo_caption", ""),
        "image_pageid": chosen.get("image_pageid"),
        "image_url": chosen.get("image_url"),
    })
    pid = chosen.get("image_pageid")
    if pid is not None and pid not in hist.setdefault("used_page_ids", []):
        hist["used_page_ids"].append(pid)
    with open(config.HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)


def main(argv: list[str]) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="только проверить, не публиковать")
    ap.add_argument("--skip-x", action="store_true")
    ap.add_argument("--skip-tg", action="store_true")
    ap.add_argument("--force", action="store_true", help="публиковать вопреки превышению лимитов")
    args = ap.parse_args(argv)

    chosen = _load_chosen()
    report = text.validate(chosen["post_tg"], chosen["post_x"], chosen["photo_caption"])
    print(f"TG подпись: {report['tg_caption_len']}/{config.TG_CAPTION_HARD_LIMIT}  "
          f"X: {report['x_weighted_len']}/{config.X_MAX}  фото-подпись: {report['photo_caption_len']}")
    if not report["ok"]:
        print("ПРОБЛЕМЫ С ДЛИНОЙ:")
        for p in report["problems"]:
            print("  - " + p)
        if not args.force:
            sys.exit("Прерываю: исправь длину (или --force).")

    caption = report["assembled_caption"]
    if args.dry_run:
        print("\n--- DRY RUN ---\nПодпись Telegram:\n" + caption + "\n\nX:\n" + chosen["post_x"])
        return

    if not args.skip_tg:
        res = send_telegram(chosen, caption)
        print(f"Telegram: ok (message_id={res.get('result', {}).get('message_id')})")
    if not args.skip_x:
        send_buffer(chosen)
        print("Buffer (X): принято в очередь на немедленную публикацию")

    update_history(chosen)
    print("История обновлена (тема + pageId фото записаны).")


if __name__ == "__main__":
    main(sys.argv[1:])
