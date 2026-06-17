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


def run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok: {fn.__name__}")
    print(f"Все тесты пройдены: {len(fns)}")


if __name__ == "__main__":
    run()
