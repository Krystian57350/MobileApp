"""Interfejs wiersza poleceń - wywoływany z PHP. Zawsze wypisuje jeden obiekt JSON."""
import argparse
import json
import sys
from datetime import date, datetime

from .config import GRANULARITIES


def _d(value):
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows: domyślnie cp1250
    p = argparse.ArgumentParser(description="Raport wydatków na subskrypcje")
    p.add_argument("--user-id", type=int, required=True)
    p.add_argument("--username", default="")
    p.add_argument("--granularity", choices=list(GRANULARITIES), default="month")
    p.add_argument("--from", dest="d_from", default="", help="RRRR-MM-DD (puste = od początku)")
    p.add_argument("--to", dest="d_to", default="", help="RRRR-MM-DD (puste = dziś)")
    p.add_argument("--format", choices=["json", "pdf"], default="json")
    p.add_argument("--output", default="", help="ścieżka pliku PDF (dla --format pdf)")
    a = p.parse_args(argv)

    try:
        # importy tu, żeby błąd brakującej biblioteki też wrócił jako JSON
        from .db import fetch_subscriptions
        from .report import build_report

        subs = fetch_subscriptions(a.user_id)
        report = build_report(subs, a.granularity, _d(a.d_from), _d(a.d_to), date.today())

        if a.format == "json":
            print(json.dumps({"success": True, "report": report}, ensure_ascii=False))
        else:
            from .charts import make_charts
            from .pdf_report import build_pdf
            if not a.output:
                raise ValueError("Brak --output dla formatu pdf.")
            with open(a.output, "wb") as fh:
                fh.write(build_pdf(report, make_charts(report), a.username))
            print(json.dumps({"success": True, "pdf": a.output}, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001 - chcemy zawsze oddać czytelny JSON do PHP
        print(json.dumps({"success": False, "message": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        sys.exit(1)
