"""Wskazówki optymalizacyjne oparte o proste reguły (bez 'magii')."""
from collections import defaultdict
from typing import List

from .formatting import money, pct
from .models import Subscription


def build_insights(subs: List[Subscription], stats: dict, buckets: List[dict]) -> List[str]:
    tips: List[str] = []
    active = [s for s in subs if s.active]
    if not active:
        return ["Nie masz aktywnych subskrypcji - nie ma czego optymalizować."]

    monthly_total = sum(s.monthly_cost for s in active)
    tips.append(f"Przy obecnych subskrypcjach wydasz ok. {money(monthly_total * 12)} rocznie "
                f"({money(monthly_total)} miesięcznie).")

    top = max(active, key=lambda s: s.monthly_cost)
    share = top.monthly_cost / monthly_total * 100 if monthly_total else 0
    if len(active) > 1 and share >= 40:
        tips.append(f"„{top.name}” to {pct(share, False)} miesięcznych kosztów. Zmiana planu lub rezygnacja "
                    f"oszczędziłaby do {money(top.monthly_cost * 12)} rocznie.")

    by_cat = defaultdict(list)
    for s in active:
        by_cat[s.category].append(s)
    for cat, items in sorted(by_cat.items()):
        if len(items) >= 2:
            names = ", ".join(f"„{s.name}”" for s in items)
            tips.append(f"W kategorii „{cat}” masz {len(items)} aktywne subskrypcje: {names} "
                        f"(razem {money(sum(s.monthly_cost for s in items))} miesięcznie). "
                        f"Sprawdź, czy potrzebujesz wszystkich.")

    if len(by_cat) > 1:
        cat, items = max(by_cat.items(), key=lambda kv: sum(s.monthly_cost for s in kv[1]))
        cat_share = sum(s.monthly_cost for s in items) / monthly_total * 100
        if cat_share >= 50 and len(items) >= 1:
            tips.append(f"Kategoria „{cat}” odpowiada za {pct(cat_share, False)} kosztów - tu szukaj oszczędności w pierwszej kolejności.")

    full = [b for b in buckets if b["complete"]]
    if len(full) >= 2 and full[-1]["change_pct"] is not None:
        ch = full[-1]["change_pct"]
        if ch >= 10:
            tips.append(f"Ostatni pełny okres był droższy o {pct(ch, False)} od poprzedniego - sprawdź, czy doszły nowe subskrypcje lub płatności roczne.")
        elif ch <= -10:
            tips.append(f"Ostatni pełny okres był tańszy o {pct(abs(ch), False)} od poprzedniego - wydatki spadają.")

    if stats.get("trend_per_period") and stats["trend_per_period"] > 0 and not stats.get("irregular"):
        tips.append(f"Trend wydatków rośnie średnio o {money(stats['trend_per_period'])} na okres.")

    return tips[:6]
