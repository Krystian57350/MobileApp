"""Przedziały czasowe: miesiąc / kwartał / półrocze / rok (kalendarzowe)."""
import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from .config import GRANULARITIES

MONTHS_PL = ["sty", "lut", "mar", "kwi", "maj", "cze",
             "lip", "sie", "wrz", "paź", "lis", "gru"]


@dataclass(frozen=True)
class Bucket:
    label: str
    start: date
    end: date  # włącznie


def add_months(d: date, n: int) -> date:
    idx = d.year * 12 + (d.month - 1) + n
    year, month = divmod(idx, 12)
    return date(year, month + 1, min(d.day, calendar.monthrange(year, month + 1)[1]))


def clamp_day(year: int, month: int, day: int) -> date:
    """Dzień płatności 31 w miesiącu z 30 dniami -> ostatni dzień miesiąca."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def bucket_start(d: date, months: int) -> date:
    first_month = (d.month - 1) // months * months + 1
    return date(d.year, first_month, 1)


def _label(start: date, granularity: str) -> str:
    if granularity == "month":
        return f"{MONTHS_PL[start.month - 1]} {start.year}"
    if granularity == "quarter":
        return f"Q{(start.month - 1) // 3 + 1} {start.year}"
    if granularity == "half":
        return f"{'I' if start.month == 1 else 'II'} poł. {start.year}"
    return str(start.year)


def build_buckets(d_from: date, d_to: date, granularity: str) -> List[Bucket]:
    if granularity not in GRANULARITIES:
        raise ValueError(f"Nieznany podział: {granularity}")
    if d_from > d_to:
        raise ValueError("Data początkowa jest późniejsza niż końcowa.")
    months = GRANULARITIES[granularity][1]
    buckets, cur = [], bucket_start(d_from, months)
    while cur <= d_to:
        nxt = add_months(cur, months)
        buckets.append(Bucket(_label(cur, granularity), cur, nxt - timedelta(days=1)))
        cur = nxt
    return buckets
