"""Główna logika: subskrypcje -> gotowy raport (słownik, serializowalny do JSON)."""
from collections import defaultdict
from datetime import date
from typing import List, Optional

from .config import GRANULARITIES, TOP_N_SUBSCRIPTIONS
from .insights import build_insights
from .models import Subscription
from .payments import build_payments
from .periods import build_buckets
from .stats import describe, pct_change


def build_report(subs: List[Subscription], granularity: str,
                 d_from: Optional[date] = None, d_to: Optional[date] = None,
                 today: Optional[date] = None) -> dict:
    today = today or date.today()
    if granularity not in GRANULARITIES:
        raise ValueError("Nieznany podział czasowy raportu.")
    d_to = min(d_to or today, today)
    meta = {"granularity": granularity, "granularity_name": GRANULARITIES[granularity][0],
            "generated": today.isoformat(), "date_from": None, "date_to": d_to.isoformat()}
    warnings: List[str] = []

    if not subs:
        return {"meta": meta, "buckets": [], "stats": describe([], []), "summary": {},
                "categories": [], "subscriptions": [], "warnings": ["Brak subskrypcji - dodaj je, aby wygenerować raport."],
                "insights": []}

    payments, w = build_payments(subs, today)
    warnings += w
    tracking_start = min(s.start for s in subs)       # od kiedy aplikacja "zna" wydatki
    d_from = max(d_from or tracking_start, tracking_start)
    if d_from > d_to:
        raise ValueError("Wybrany zakres kończy się przed pierwszą subskrypcją.")
    meta["date_from"] = d_from.isoformat()

    buckets = []
    prev = None
    for b in build_buckets(d_from, d_to, granularity):
        in_b = [p for p in payments if b.start <= p.date <= b.end]
        by_cat = defaultdict(float)
        for p in in_b:
            by_cat[p.category] += p.amount
        if b.end >= today:
            status = "in_progress"       # bieżący okres jeszcze trwa
        elif b.start < tracking_start:
            status = "partial_start"     # okres zaczął się przed rozpoczęciem śledzenia
        else:
            status = "complete"
        item = {"label": b.label, "start": b.start.isoformat(), "end": b.end.isoformat(),
                "total": round(sum(by_cat.values()), 2),
                "by_category": {k: round(v, 2) for k, v in by_cat.items()},
                "status": status, "complete": status == "complete", "change_pct": None}
        if item["complete"] and prev and prev["complete"]:
            item["change_pct"] = pct_change(item["total"], prev["total"])
            if item["change_pct"] is not None:
                item["change_pct"] = round(item["change_pct"], 1)
        buckets.append(item)
        prev = item

    # puste okresy na początku (przed pierwszą płatnością) nic nie wnoszą - pomijamy
    while buckets and buckets[0]["status"] == "partial_start" and buckets[0]["total"] == 0:
        buckets.pop(0)
    if buckets:
        meta["date_from"] = buckets[0]["start"]
    if buckets and buckets[0]["status"] == "partial_start":
        buckets[0]["change_pct"] = None

    full = [b for b in buckets if b["complete"]]
    stats = describe([b["total"] for b in full], [b["label"] for b in full])
    if any(not b["complete"] for b in buckets):
        stats["notes"].append("Okresy niepełne (trwający lub rozpoczęty przed pierwszą subskrypcją) "
                              "są na wykresie, ale nie wchodzą do średniej i mediany.")

    active = [s for s in subs if s.active]
    monthly_now = sum(s.monthly_cost for s in active)
    summary = {"monthly_now": round(monthly_now, 2), "yearly_projection": round(monthly_now * 12, 2),
               "active": len(active), "inactive": len(subs) - len(active),
               "tracking_start": tracking_start.isoformat(),
               "total_range": round(sum(b["total"] for b in buckets), 2)}

    if not buckets:
        return {"meta": meta, "buckets": [], "stats": stats, "summary": summary, "categories": [],
                "subscriptions": [], "insights": [], "warnings": warnings + ["Brak płatności w wybranym zakresie."]}
    range_total = summary["total_range"]
    cat_total, cat_monthly = defaultdict(float), defaultdict(float)
    for b in buckets:
        for k, v in b["by_category"].items():
            cat_total[k] += v
    for s in active:
        cat_monthly[s.category] += s.monthly_cost
    categories = [{"name": k, "total": round(cat_total.get(k, 0), 2),
                   "share": round(cat_total.get(k, 0) / range_total * 100, 1) if range_total else 0,
                   "monthly_now": round(cat_monthly.get(k, 0), 2)}
                  for k in sorted(set(cat_total) | set(cat_monthly), key=lambda c: -cat_total.get(c, 0))]

    in_range = defaultdict(float)
    lo, hi = buckets[0]["start"], buckets[-1]["end"]
    for p in payments:
        if lo <= p.date.isoformat() <= hi:
            in_range[p.sub_id] += p.amount
    ranked = sorted(active, key=lambda s: -s.monthly_cost)[:TOP_N_SUBSCRIPTIONS]
    subscriptions = [{"name": s.name, "category": s.category, "cost": s.cost, "period": s.period,
                      "monthly_cost": round(s.monthly_cost, 2),
                      "share": round(s.monthly_cost / monthly_now * 100, 1) if monthly_now else 0,
                      "total_in_range": round(in_range.get(s.id, 0), 2)} for s in ranked]

    return {"meta": meta, "buckets": buckets, "stats": stats, "summary": summary,
            "categories": categories, "subscriptions": subscriptions,
            "insights": build_insights(subs, stats, buckets), "warnings": warnings}
