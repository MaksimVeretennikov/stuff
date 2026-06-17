"""GET с User-Agent и ретраями (экспоненциальная пауза). Зависим только от requests."""

from __future__ import annotations

import time

import requests

from . import config

DEFAULT_TIMEOUT = 20


def get(url: str, *, params: dict | None = None, headers: dict | None = None,
        retries: int = 4, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    h = {"User-Agent": config.WIKIMEDIA_UA}
    if headers:
        h.update(headers)
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=h, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001 — best-effort, важна устойчивость
            last = e
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))  # 2s, 4s, 8s
    raise last  # type: ignore[misc]


def get_json(url: str, **kwargs) -> dict:
    return get(url, **kwargs).json()


def mediawiki_parse(api_base: str, page: str, *, prop: str = "wikitext") -> str | None:
    """Текст статьи через стабильный action=parse (вместо хрупкого парсинга HTML)."""
    try:
        data = get_json(
            f"{api_base}/w/api.php",
            params={
                "action": "parse",
                "page": page,
                "prop": prop,
                "format": "json",
                "redirects": 1,
            },
        )
    except Exception:
        return None
    if "error" in data:
        return None
    parse = data.get("parse", {})
    if prop == "wikitext":
        return parse.get("wikitext", {}).get("*")
    return parse.get("text", {}).get("*")
