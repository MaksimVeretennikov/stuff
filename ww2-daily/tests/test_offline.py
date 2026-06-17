"""Офлайн-тесты логики, не требующей сети. Запуск: python -m tests.test_offline"""

import json
import os
import tempfile

from ww2daily import config, text
from ww2daily import find_photos
from ww2daily.fetch_sources import parse_onwar, extract_day_lines


def test_parse_onwar():
    html = (
        "<html><body>"
        "<h2>Tuesday, June 17, 1941</h2>"
        "<p>Event <b>one</b> happened.</p>"
        "<p>Event two happened.</p>"
        "<hr>"
        "<h2>Wednesday, June 18, 1941</h2>"
        "<p>Should not appear.</p>"
        "</body></html>"
    )
    out = parse_onwar(html, "Tuesday, June 17, 1941")
    assert out == "Event one happened.\n\nEvent two happened.", repr(out)
    assert "Should not appear" not in out


def test_extract_day_lines():
    plain = "17 июня началось\n18 июня другое\n17 июня ещё событие"
    out = extract_day_lines(plain, ["17 июня"])
    assert "началось" in out and "ещё событие" in out
    assert "другое" not in out


def test_text_limits():
    assert text.x_weighted_len("Hello 🇩🇪 https://example.com/x") == 6 + 4 + 1 + 23
    rep = text.validate("<b>17 июня 1941</b>\n\nКороткий пост.", "Short.", "Подпись")
    assert rep["ok"], rep
    long_x = "x" * 281
    assert not text.validate("ok", long_x, "c")["ok"]


def test_photo_dedup_and_year(monkeypatched=None):
    pages = {
        "111": {"pageid": 111, "title": "File:A.jpg", "imageinfo": [{
            "thumburl": "http://x/A.jpg",
            "extmetadata": {"DateTimeOriginal": {"value": "1941-06-17"},
                            "ImageDescription": {"value": "<p>German troops</p>"}}}]},
        "222": {"pageid": 222, "title": "File:B.jpg", "imageinfo": [{
            "thumburl": "http://x/B.jpg",
            "extmetadata": {"DateTimeOriginal": {"value": "1998"},
                            "ImageDescription": {"value": "Modern reenactment"}}}]},
        "333": {"pageid": 333, "title": "File:C.jpg", "imageinfo": [{
            "thumburl": "http://x/C.jpg",
            "extmetadata": {"DateTimeOriginal": {"value": "1940"},
                            "ImageDescription": {"value": "Used already"}}}]},
    }
    # подменяем сетевые функции и историю
    find_photos.search_files = lambda q: pages
    find_photos.search_category_files = lambda q: {}
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump({"posts": [], "used_page_ids": [333]}, tmp, ensure_ascii=False)
    tmp.close()
    old = config.HISTORY_PATH
    config.HISTORY_PATH = tmp.name
    try:
        cands = find_photos.build_candidates("anything", "")
    finally:
        config.HISTORY_PATH = old
        os.unlink(tmp.name)
    ids = [c["pageid"] for c in cands]
    assert ids == [111], ids          # 222 отсечён по году (>1950), 333 — как использованный
    assert cands[0]["description"] == "German troops"


def test_target_date_override():
    import datetime as dt
    from ww2daily.dates import TargetDate
    td = TargetDate(dt.datetime(2026, 6, 22, 9, 30))
    assert td.human_ru == "22 июня 1941", td.human_ru
    assert td.year == 1941 and td.month == 6 and td.day == 22


def test_migration_record_and_history():
    from ww2daily import migrate_airtable as mig
    from ww2daily import config
    rec_fields = {
        config.AIRTABLE_FIELD_DATE: "17.06.2026",
        config.AIRTABLE_FIELD_POST_X: "June 17, 1941 — Hitler sets the date.",
        config.AIRTABLE_FIELD_CAPTION: "Гитлер на совещании, 1941",
        config.AIRTABLE_FIELD_PAGEID: "12345",
    }
    p = mig.record_to_post(rec_fields)
    assert p["date_ww2"] == "17.06.1941", p["date_ww2"]
    assert p["image_pageid"] == 12345
    assert p["title"].startswith("Гитлер")

    records = [
        {"fields": {config.AIRTABLE_FIELD_DATE: "18.06.2026",
                    config.AIRTABLE_FIELD_PAGEID: "222"}},
        {"fields": {config.AIRTABLE_FIELD_DATE: "17.06.2026",
                    config.AIRTABLE_FIELD_PAGEID: "111"}},
        {"fields": {config.AIRTABLE_FIELD_DATE: "19.06.2026",
                    config.AIRTABLE_FIELD_PAGEID: "111"}},  # дубль pageId
    ]
    hist = mig.build_history(records)
    assert hist["used_page_ids"] == [111, 222], hist["used_page_ids"]  # уникальные, по порядку дат
    assert [p["date_ww2"] for p in hist["posts"]] == ["17.06.1941", "18.06.1941", "19.06.1941"]


def run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok: {fn.__name__}")
    print(f"Все тесты пройдены: {len(fns)}")


if __name__ == "__main__":
    run()
