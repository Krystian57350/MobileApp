"""Statystyki opisowe z regułami 'kiedy dana miara ma sens'.

Używamy wyłącznie biblioteki standardowej (statistics) - dla kilkudziesięciu
wartości pandas/numpy nie są potrzebne.
"""
import statistics
from typing import List, Optional, Sequence

from . import config


def pct_change(new: float, old: Optional[float]) -> Optional[float]:
    if old is None or old == 0:
        return None
    return (new - old) / old * 100


def describe(values: Sequence[float], labels: Sequence[str]) -> dict:
    """Statystyki z PEŁNYCH okresów. Miary, które nie mają sensu, zwracają None
    i trafiają na listę `notes` z uzasadnieniem."""
    n = len(values)
    out = {"n": n, "total": round(sum(values), 2), "mean": None, "median": None,
           "min": None, "max": None, "stdev": None, "cv": None,
           "trend_per_period": None, "irregular": False, "notes": []}
    notes: List[str] = out["notes"]

    if n == 0:
        notes.append("Brak pełnych okresów w wybranym zakresie - nie liczę średniej ani mediany.")
        return out

    if out["total"] == 0:
        notes.append("W pełnych okresach nie było żadnych płatności (np. subskrypcje roczne) - średnia 0 zł nie "
                     "opisuje kosztów. Zobacz koszt miesięczny przeliczony z płatności rocznych.")
        return out

    i_min = min(range(n), key=values.__getitem__)
    i_max = max(range(n), key=values.__getitem__)
    out["min"] = {"value": round(values[i_min], 2), "label": labels[i_min]}
    out["max"] = {"value": round(values[i_max], 2), "label": labels[i_max]}

    if n >= config.MIN_PERIODS_MEAN:
        out["mean"] = round(statistics.fmean(values), 2)
    else:
        notes.append("Średnia wymaga co najmniej 2 pełnych okresów - wybierz dłuższy zakres.")

    if n >= config.MIN_PERIODS_MEDIAN:
        out["median"] = round(statistics.median(values), 2)
        out["stdev"] = round(statistics.stdev(values), 2)
        if out["mean"]:
            out["cv"] = round(out["stdev"] / out["mean"], 2)
    elif n >= config.MIN_PERIODS_MEAN:
        notes.append("Mediana i odchylenie standardowe mają sens od 3 pełnych okresów.")

    if n >= config.MIN_PERIODS_TREND:
        slope = statistics.linear_regression(range(n), values).slope
        out["trend_per_period"] = round(slope, 2)

    if out["median"] is not None and out["mean"]:
        gap = abs(out["mean"] - out["median"]) / out["median"] if out["median"] else 0
        if (out["cv"] or 0) > config.IRREGULAR_CV or gap > config.MEAN_MEDIAN_GAP:
            out["irregular"] = True
            notes.append("Wydatki są nieregularne (np. płatności roczne) - średnia jest zniekształcona, "
                         "dla typowego okresu lepiej patrzeć na medianę.")
    return out
