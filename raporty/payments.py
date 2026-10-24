"""Odtwarzanie historii płatności.

Aplikacja nie przechowuje historii płatności, tylko definicje subskrypcji.
Historię odtwarzamy: płatność w dniu z `nextDate` co miesiąc (lub co rok),
od daty dodania subskrypcji do dziś albo do daty dezaktywacji.
"""
from datetime import date
from typing import Iterator, List, Tuple

from .models import Payment, Subscription
from .periods import clamp_day


def charge_dates(sub: Subscription, today: date) -> Iterator[date]:
    if not sub.active and sub.end is None:
        return  # brak daty zakończenia - nie zgadujemy (patrz report.py -> ostrzeżenie)
    last = min(today, sub.end) if sub.end else today
    anchor = sub.next_date or sub.start

    if sub.period == "yearly":
        for year in range(sub.start.year, last.year + 1):
            d = clamp_day(year, anchor.month, anchor.day)
            if sub.start <= d <= last:
                yield d
    else:
        year, month = sub.start.year, sub.start.month
        while (year, month) <= (last.year, last.month):
            d = clamp_day(year, month, anchor.day)
            if sub.start <= d <= last:
                yield d
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def build_payments(subs: List[Subscription], today: date) -> Tuple[List[Payment], List[str]]:
    payments, warnings = [], []
    for s in subs:
        if not s.active and s.end is None:
            warnings.append(f"„{s.name}” jest nieaktywna, ale nie ma daty zakończenia - pominięto w historii.")
            continue
        payments.extend(Payment(s.id, s.name, s.category, s.cost, d) for d in charge_dates(s, today))
    return payments, warnings
