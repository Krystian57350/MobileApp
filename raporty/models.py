from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Subscription:
    id: str
    name: str
    cost: float
    period: str                 # 'monthly' | 'yearly'
    next_date: Optional[date]   # data następnej płatności (kotwica dnia płatności)
    category: str
    active: bool
    start: date                 # data dodania subskrypcji do aplikacji
    end: Optional[date]         # data dezaktywacji (kolumna end_date), None = trwa

    @property
    def monthly_cost(self) -> float:
        """Koszt przeliczony na miesiąc (roczne / 12) - tak samo jak w script.js."""
        return self.cost / 12 if self.period == "yearly" else self.cost


@dataclass(frozen=True)
class Payment:
    sub_id: str
    name: str
    category: str
    amount: float
    date: date
