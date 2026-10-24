"""Warstwa dostępu do bazy - jedyne miejsce, które zna MySQL."""
from datetime import date, datetime
from typing import List

from libs import pymysql

from .config import DB
from .models import Subscription


def _to_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def fetch_subscriptions(user_id: int) -> List[Subscription]:
    conn = pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB)
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM subskrypcje LIKE 'end_date'")
            has_end = cur.fetchone() is not None
            cols = "id,name,cost,period,nextDate,category,active,added"
            if has_end:
                cols += ",end_date"
            cur.execute(f"SELECT {cols} FROM subskrypcje WHERE user_id = %s", (int(user_id),))
            rows = cur.fetchall()
    finally:
        conn.close()

    subs = []
    for r in rows:
        subs.append(Subscription(
            id=r["id"],
            name=r["name"],
            cost=float(r["cost"]),
            period=r["period"],
            next_date=_to_date(r["nextDate"]),
            category=r["category"] or "Brak kategorii",
            active=bool(r["active"]),
            start=datetime.fromtimestamp(int(r["added"]) / 1000).date(),
            end=_to_date(r.get("end_date")) if has_end else None,
        ))
    return subs
