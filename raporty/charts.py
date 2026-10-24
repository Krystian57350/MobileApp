"""Wykresy słupkowe (matplotlib) zwracane jako PNG w pamięci."""
import io
from typing import Dict, Optional

import matplotlib

matplotlib.use("Agg")  # bez okna - działa na serwerze
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from .config import CURRENCY

BLUE, LIGHT, GREEN, ORANGE = "#2563eb", "#93b4f5", "#059669", "#d97706"
PALETTE = ["#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#64748b"]


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _axis(ax):
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", " ")))
    ax.set_ylabel(CURRENCY)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=.25)
    ax.set_axisbelow(True)


def totals_chart(report: dict) -> bytes:
    b = report["buckets"]
    labels = [x["label"] for x in b]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    bars = ax.bar(labels, [x["total"] for x in b],
                  color=[BLUE if x["complete"] else LIGHT for x in b],
                  hatch=None, edgecolor="white")
    for bar, x in zip(bars, b):
        if not x["complete"]:
            bar.set_hatch("//")
        ax.annotate(f"{x['total']:,.0f}".replace(",", " "), (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha="center", va="bottom", fontsize=8, xytext=(0, 2), textcoords="offset points")
    st = report["stats"]
    if st["mean"] is not None:
        ax.axhline(st["mean"], color=GREEN, ls="--", lw=1.3, label=f"średnia: {st['mean']:,.0f} {CURRENCY}".replace(",", " "))
    if st["median"] is not None:
        ax.axhline(st["median"], color=ORANGE, ls=":", lw=1.5, label=f"mediana: {st['median']:,.0f} {CURRENCY}".replace(",", " "))
    ax.set_title(f"Wydatki - zestawienie {report['meta']['granularity_name']}", fontsize=11, loc="left")
    _axis(ax)
    if ax.get_legend_handles_labels()[0]:
        ax.set_ylim(0, max(x["total"] for x in b) * 1.3 or 1)   # miejsce na legendę nad słupkami
        ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    if len(labels) > 6:
        plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    return _png(fig)


def stacked_chart(report: dict) -> Optional[bytes]:
    b = report["buckets"]
    cats = [c["name"] for c in report["categories"]]
    if len(cats) < 2:
        return None  # jedna kategoria - wykres skumulowany nic nie wnosi
    labels = [x["label"] for x in b]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    bottom = [0] * len(b)
    for i, cat in enumerate(cats):
        vals = [x["by_category"].get(cat, 0) for x in b]
        ax.bar(labels, vals, bottom=bottom, label=cat, color=PALETTE[i % len(PALETTE)], edgecolor="white")
        bottom = [a + v for a, v in zip(bottom, vals)]
    ax.set_title("Struktura wydatków wg kategorii", fontsize=11, loc="left")
    _axis(ax)
    ax.set_ylim(0, max(bottom) * 1.3 or 1)
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=min(len(cats), 4))
    if len(labels) > 6:
        plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    return _png(fig)


def top_subs_chart(report: dict) -> Optional[bytes]:
    subs = report["subscriptions"]
    if not subs:
        return None
    fig, ax = plt.subplots(figsize=(8, 0.45 * len(subs) + 1.2))
    names = [s["name"] for s in subs][::-1]
    vals = [s["monthly_cost"] for s in subs][::-1]
    bars = ax.barh(names, vals, color=BLUE)
    for bar, v in zip(bars, vals):
        ax.annotate(f"{v:,.2f} {CURRENCY}".replace(",", " ").replace(".", ","), (v, bar.get_y() + bar.get_height() / 2),
                    va="center", xytext=(4, 0), textcoords="offset points", fontsize=8)
    ax.set_title("Najdroższe subskrypcje (koszt miesięczny)", fontsize=11, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, max(vals) * 1.2)
    ax.set_xlabel(f"{CURRENCY} / miesiąc")
    return _png(fig)


def make_charts(report: dict) -> Dict[str, Optional[bytes]]:
    if not report["buckets"]:
        return {}
    return {"totals": totals_chart(report), "stacked": stacked_chart(report), "top": top_subs_chart(report)}
