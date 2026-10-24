"""Konfiguracja modułu raportów. Domyślnie takie same dane jak w db.php (XAMPP)."""
import os

DB = {
    "host": os.getenv("MS_DB_HOST", "127.0.0.1"),
    "user": os.getenv("MS_DB_USER", "root"),
    "password": os.getenv("MS_DB_PASS", ""),
    "database": os.getenv("MS_DB_NAME", "menadzer_subskrypcji"),
    "charset": "utf8mb4",
}

# klucz -> (nazwa po polsku, liczba miesięcy w jednym przedziale)
GRANULARITIES = {
    "month": ("miesięczne", 1),
    "quarter": ("kwartalne", 3),
    "half": ("półroczne", 6),
    "year": ("roczne", 12),
}

# Kiedy statystyka ma sens (liczba PEŁNYCH okresów):
MIN_PERIODS_MEAN = 2      # średnia od 2 okresów
MIN_PERIODS_MEDIAN = 3    # mediana i odchylenie od 3 okresów
MIN_PERIODS_TREND = 4     # trend (regresja liniowa) od 4 okresów
IRREGULAR_CV = 0.5        # współczynnik zmienności powyżej tego = wydatki nieregularne
MEAN_MEDIAN_GAP = 0.25    # różnica średnia/mediana powyżej 25% = ostrzeżenie

CURRENCY = "zł"
TOP_N_SUBSCRIPTIONS = 8
