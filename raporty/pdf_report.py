"""Generowanie PDF (reportlab). Czcionka DejaVu z matplotlib - ma polskie znaki."""
import io
import os

import matplotlib
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from .formatting import money, pct

_FONT_DIR = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(_FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")

BLUE = colors.HexColor("#2563eb")
STATUS = {"complete": "pełny", "in_progress": "w toku", "partial_start": "niepełny",
          "partial_range": "niepełny"}


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontName="DejaVu-Bold", fontSize=20, textColor=BLUE, alignment=0),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="DejaVu-Bold", fontSize=13, textColor=BLUE, spaceBefore=10, spaceAfter=4),
        "p": ParagraphStyle("p", parent=base["BodyText"], fontName="DejaVu", fontSize=9.5, leading=13),
        "small": ParagraphStyle("s", parent=base["BodyText"], fontName="DejaVu", fontSize=8, leading=11, textColor=colors.HexColor("#475569")),
        "cell": ParagraphStyle("c", parent=base["BodyText"], fontName="DejaVu", fontSize=8.5, leading=11),
    }


def _table(data, col_widths, align_right_from=1):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _img(png: bytes, width_cm=17):
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(io.BytesIO(png)).getSize()
    return Image(io.BytesIO(png), width=width_cm * cm, height=width_cm * cm * h / w)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("DejaVu", 7.5)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(2 * cm, 1.2 * cm, "Menadżer subskrypcji - raport wydatków")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Strona {doc.page}")
    canvas.restoreState()


def build_pdf(report: dict, charts: dict, username: str = "") -> bytes:
    S, m, st, sm = _styles(), report["meta"], report["stats"], report["summary"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=2 * cm, title="Raport wydatków na subskrypcje")
    f = []
    f.append(Paragraph("Raport wydatków na subskrypcje", S["title"]))
    who = f"Użytkownik: <b>{username}</b> &nbsp;|&nbsp; " if username else ""
    f.append(Paragraph(f"{who}Zestawienie: <b>{m['granularity_name']}</b> &nbsp;|&nbsp; "
                       f"Zakres: <b>{m['date_from'] or '-'}</b> - <b>{m['date_to']}</b> &nbsp;|&nbsp; "
                       f"Wygenerowano: {m['generated']}", S["p"]))
    for w in report["warnings"]:
        f.append(Paragraph(f"⚠ {w}", S["small"]))

    if not report["buckets"]:
        doc.build(f, onFirstPage=_footer, onLaterPages=_footer)
        return buf.getvalue()

    f.append(Paragraph("Podsumowanie", S["h2"]))
    na = "brak (za mało okresów)"
    rows = [["Wskaźnik", "Wartość"],
            ["Suma wydatków w zakresie", money(sm["total_range"])],
            [f"Średnia na okres ({st['n']} pełnych)", money(st["mean"]) if st["mean"] is not None else na],
            ["Mediana", money(st["median"]) if st["median"] is not None else na],
            ["Najmniej / najwięcej", f"{money(st['min']['value'])} ({st['min']['label']}) / {money(st['max']['value'])} ({st['max']['label']})" if st["min"] else "-"],
            ["Odchylenie standardowe", money(st["stdev"]) if st["stdev"] is not None else na],
            ["Obecny koszt miesięczny (aktywne)", money(sm["monthly_now"])],
            ["Prognoza roczna przy obecnych subskrypcjach", money(sm["yearly_projection"])]]
    f.append(_table(rows, [8 * cm, 9 * cm]))
    for n in st["notes"]:
        f.append(Paragraph(f"• {n}", S["small"]))

    if charts.get("totals"):
        f += [Spacer(1, 8), _img(charts["totals"])]

    f.append(Paragraph("Zestawienie okresów", S["h2"]))
    rows = [["Okres", "Suma", "Zmiana vs poprz.", "Status"]]
    for b in report["buckets"]:
        rows.append([b["label"], money(b["total"]), pct(b["change_pct"]), STATUS[b["status"]]])
    f.append(_table(rows, [5 * cm, 4 * cm, 4 * cm, 4 * cm]))

    if charts.get("stacked"):
        f += [Spacer(1, 8), _img(charts["stacked"])]

    cat_block = [Paragraph("Kategorie", S["h2"])]
    rows = [["Kategoria", "Suma w zakresie", "Udział", "Koszt mies. (aktywne)"]]
    for c in report["categories"]:
        rows.append([c["name"], money(c["total"]), pct(c["share"], False), money(c["monthly_now"])])
    cat_block.append(_table(rows, [5.5 * cm, 4 * cm, 3 * cm, 4.5 * cm]))
    f.append(KeepTogether(cat_block))

    if report["subscriptions"]:
        f.append(Paragraph("Najdroższe subskrypcje", S["h2"]))
        rows = [["Nazwa", "Kategoria", "Cena", "Miesięcznie", "Udział"]]
        for s in report["subscriptions"]:
            per = "rocznie" if s["period"] == "yearly" else "mies."
            rows.append([Paragraph(s["name"], S["cell"]), Paragraph(s["category"], S["cell"]),
                         f"{money(s['cost'])} / {per}", money(s["monthly_cost"]), pct(s["share"], False)])
        f.append(_table(rows, [4.5 * cm, 3.5 * cm, 3.6 * cm, 3 * cm, 2.4 * cm], align_right_from=2))
        if charts.get("top"):
            f += [Spacer(1, 8), _img(charts["top"], 15)]

    f.append(Paragraph("Jak obniżyć wydatki", S["h2"]))
    for tip in report["insights"]:
        f.append(Paragraph(f"• {tip}", S["p"]))

    f.append(Paragraph("Jak czytać ten raport", S["h2"]))
    for txt in [
        "Historia płatności jest odtwarzana z danych subskrypcji (data dodania, dzień płatności, okres rozliczeniowy), "
        "ponieważ aplikacja nie zapisuje pojedynczych płatności.",
        "Średnia, mediana i odchylenie liczone są tylko z pełnych okresów. Okresy w toku lub rozpoczęte przed "
        "pierwszą subskrypcją są pokazane, ale pomijane w statystykach.",
        "Dla pojedynczej subskrypcji nie liczymy średniej w czasie (cena jest stała) - podajemy koszt miesięczny "
        "(płatności roczne podzielone przez 12).",
    ]:
        f.append(Paragraph(f"• {txt}", S["small"]))

    doc.build(f, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
