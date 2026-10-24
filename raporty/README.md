# Moduł raportów (Python)

Raport wydatków na subskrypcje: zestawienie miesięczne / kwartalne / półroczne / roczne,
statystyki (średnia, mediana, odchylenie, trend), wykresy słupkowe, wskazówki oszczędzania, eksport do PDF.

## Instalacja (Windows + XAMPP)
1. Aplikacja domyślnie używa Pythona 3.15 z `%LOCALAPPDATA%\Programs\Python\Python315\python.exe` (np. `C:\Users\nazwa_uzytkownika\AppData\Local\Programs\Python\Python315\python.exe`).
2. Zależności raportów są dołączone w głównym folderze `libs` i ładowane stamtąd przez `raporty/run.py`. Nie trzeba instalować ich globalnie ani w środowisku Pythona.
3. Baza danych NIE wymaga żadnych zmian.
4. Jeśli Python jest zainstalowany w innym miejscu, ustaw zmienną środowiskową `PYTHON_BIN` na pełną ścieżkę do odpowiedniego `python.exe`.
5. Dane do bazy są w `raporty/config.py` (domyślnie jak w `db.php`: 127.0.0.1, root, bez hasła).

## Test z wiersza poleceń
    python raporty/run.py --user-id 1 --granularity month --format json
    python raporty/run.py --user-id 1 --granularity quarter --from 2026-01-01 --format pdf --output raport.pdf
    python -m unittest discover -s raporty/tests -t .

## Moduły
| plik | zadanie |
|---|---|
| `db.py` | jedyne miejsce z SQL (pobranie subskrypcji) |
| `periods.py` | przedziały: miesiąc / kwartał / półrocze / rok |
| `payments.py` | odtworzenie historii płatności z definicji subskrypcji |
| `stats.py` | średnia, mediana, odchylenie, trend + reguły "kiedy ma to sens" |
| `insights.py` | wskazówki optymalizacyjne |
| `report.py` | składa wszystko w jeden słownik (JSON) |
| `charts.py` / `pdf_report.py` | wykresy matplotlib / PDF reportlab |
| `cli.py`, `run.py` | wejście wołane z PHP |

## Kiedy liczymy średnią
- Tylko z **pełnych** okresów (bieżący i rozpoczęty przed pierwszą subskrypcją są na wykresie, ale poza statystyką).
- Średnia od 2 okresów, mediana i odchylenie od 3, trend od 4. Poniżej: komunikat zamiast liczby.
- Okresy z samymi zerami (np. tylko płatność roczna) nie dają "średniej 0 zł".
- Płatności roczne psują średnią -> raport to wykrywa i zaleca medianę.
- Dla pojedynczej subskrypcji nie ma średniej w czasie (stała cena) - pokazujemy koszt miesięczny (roczne / 12).

## Ograniczenia
Aplikacja nie zapisuje pojedynczych płatności, więc historia jest odtwarzana: od daty dodania subskrypcji,
w dniu z "Data następnej płatności", do dziś.
Subskrypcje **nieaktywne** nie mają zapisanej daty zakończenia, więc są pomijane w historii (raport wyświetla
ostrzeżenie z ich nazwami); wchodzą tylko do liczby nieaktywnych. Jeśli kiedyś dodacie kolumnę `end_date`
(DATE NULL) i zapis daty przy dezaktywacji, moduł użyje jej automatycznie. Zmiana ceny w czasie nie jest uwzględniana
(wymagałoby tabeli `platnosci`).
