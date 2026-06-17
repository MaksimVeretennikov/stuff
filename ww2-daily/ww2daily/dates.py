"""Вычисление целевой даты («85 лет назад») и её форматов.

Локали в контейнерах ненадёжны, поэтому имена месяцев/дней — фиксированными
таблицами, без locale.setlocale.
"""

from __future__ import annotations

import datetime as _dt
from zoneinfo import ZoneInfo

from . import config

EN_WEEKDAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]
EN_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
# Родительный падеж — для «17 июня 1941».
RU_MONTHS_GEN = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]
# Именительный падеж — для названия статьи «Хроника ... (июнь 1941 года)».
RU_MONTHS_NOM = [
    "", "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]


def now_msk() -> _dt.datetime:
    return _dt.datetime.now(ZoneInfo(config.TIMEZONE))


def subtract_years(d: _dt.date, years: int) -> _dt.date:
    """Корректно вычесть годы (с обработкой 29 февраля)."""
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        # 29 февраля -> 28 февраля
        return d.replace(year=d.year - years, day=28)


class TargetDate:
    """Все нужные представления целевой даты."""

    def __init__(self, base: _dt.datetime | None = None):
        base = base or now_msk()
        self.today: _dt.date = base.date()
        self.target: _dt.date = subtract_years(self.today, config.YEARS_BACK)

    @property
    def year(self) -> int:
        return self.target.year

    @property
    def month(self) -> int:
        return self.target.month

    @property
    def day(self) -> int:
        return self.target.day

    # --- строковые форматы ---
    @property
    def yyyymm(self) -> str:
        return f"{self.year:04d}{self.month:02d}"

    @property
    def mm(self) -> str:
        return f"{self.month:02d}"

    @property
    def dd(self) -> str:
        return f"{self.day:02d}"

    @property
    def human_ru(self) -> str:
        """«17 июня 1941»."""
        return f"{self.day} {RU_MONTHS_GEN[self.month]} {self.year}"

    @property
    def dotted(self) -> str:
        """«17.06.1941»."""
        return f"{self.dd}.{self.mm}.{self.year:04d}"

    @property
    def onwar_header(self) -> str:
        """«Tuesday, June 17, 1941» — для поиска блока дня на onwar.com."""
        wd = EN_WEEKDAYS[self.target.weekday()]
        return f"{wd}, {EN_MONTHS[self.month]} {self.day}, {self.year}"

    @property
    def ru_month_nom(self) -> str:
        return RU_MONTHS_NOM[self.month]

    def as_dict(self) -> dict:
        return {
            "today_iso": self.today.isoformat(),
            "target_iso": self.target.isoformat(),
            "human_ru": self.human_ru,
            "dotted": self.dotted,
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "yyyymm": self.yyyymm,
            "onwar_header": self.onwar_header,
            "ru_month_nom": self.ru_month_nom,
        }
