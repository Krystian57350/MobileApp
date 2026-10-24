from .config import CURRENCY


def money(value: float) -> str:
    """1234.5 -> '1 234,50 zł' (twarda spacja, żeby kwota nie łamała się w PDF)."""
    if value is None:
        return "-"
    txt = f"{value:,.2f}".replace(",", "\u00a0").replace(".", ",")
    if txt.endswith(",00"):
        txt = txt[:-3]
    return f"{txt}\u00a0{CURRENCY}"


def pct(value, signed: bool = True) -> str:
    if value is None:
        return "-"
    if signed and round(value, 1) == 0:
        return "0,0%"
    return f"{value:+.1f}%".replace(".", ",") if signed else f"{value:.1f}%".replace(".", ",")
