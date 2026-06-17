"""Проверка длины и сборка подписи. Здесь — единственный источник правды про лимиты,
чтобы X не ругался на «превышение символов», а Telegram не обрезал подпись."""

from __future__ import annotations

import re

from . import config

_URL_RE = re.compile(r"https?://\S+")


def utf16_len(s: str) -> int:
    """Длина в UTF-16 code units — именно так считает лимит подписи Telegram."""
    return len(s.encode("utf-16-le")) // 2


def x_weighted_len(text: str) -> int:
    """Взвешенная длина для X: URL = 23, emoji/CJK = 2, остальное = 1."""
    urls = _URL_RE.findall(text)
    rest = _URL_RE.sub("", text)
    n = 0
    for ch in rest:
        o = ord(ch)
        if (
            0x1100 <= o <= 0x115F
            or 0x2E80 <= o <= 0xA4CF
            or 0xAC00 <= o <= 0xD7A3
            or 0xF900 <= o <= 0xFAFF
            or 0xFE30 <= o <= 0xFE4F
            or 0xFF00 <= o <= 0xFF60
            or 0xFFE0 <= o <= 0xFFE6
            or 0x1F000 <= o <= 0x1FAFF
            or 0x2600 <= o <= 0x27BF
            or 0x1F1E6 <= o <= 0x1F1FF
        ):
            n += 2
        else:
            n += 1
    return n + 23 * len(urls)


def escape_caption(text: str) -> str:
    """Экранируем только спецсимволы HTML в подписи к фото (тегов там нет)."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def assemble_tg_caption(photo_caption: str, post_tg: str) -> str:
    """«<i>{подпись к фото}</i>\\n\\n{пост}». Пост отдаём как есть — в нём теги <b> от модели."""
    cap = escape_caption(photo_caption.strip())
    return f"<i>{cap}</i>\n\n{post_tg.strip()}"


def validate(post_tg: str, post_x: str, photo_caption: str) -> dict:
    """Вернуть отчёт о соответствии лимитам. Ничего не обрезает — только диагностирует,
    чтобы Claude в рутине переписал то, что вышло за рамки."""
    caption = assemble_tg_caption(photo_caption, post_tg)
    cap_len = utf16_len(caption)
    xlen = x_weighted_len(post_x)
    problems = []
    if cap_len > config.TG_CAPTION_HARD_LIMIT:
        problems.append(
            f"Подпись Telegram {cap_len} > {config.TG_CAPTION_HARD_LIMIT} "
            f"(жёсткий лимит). Сократи пост/подпись к фото."
        )
    if utf16_len(photo_caption) > config.PHOTO_CAPTION_MAX:
        problems.append(
            f"Подпись к фото {utf16_len(photo_caption)} > {config.PHOTO_CAPTION_MAX}."
        )
    if xlen > config.X_MAX:
        problems.append(f"Пост X взвешенно {xlen} > {config.X_MAX}.")
    return {
        "ok": not problems,
        "tg_caption_len": cap_len,
        "photo_caption_len": utf16_len(photo_caption),
        "x_weighted_len": xlen,
        "problems": problems,
        "assembled_caption": caption,
    }
