# MobileApp

## Wersja GitHub Pages (bez PHP i MySQL)

Repozytorium zawiera statyczną wersję aplikacji w `index.html`. Działa w przeglądarce bez XAMPP, PHP i bazy MySQL.

### Publikacja

1. Wypchnij pliki aplikacji do repozytorium GitHub.
2. Otwórz **Settings → Pages**.
3. W sekcji **Build and deployment** wybierz **Deploy from a branch**, następnie gałąź z aplikacją i folder **/(root)**.
4. Zapisz ustawienia. Po zakończeniu publikacji GitHub pokaże adres strony.

### Dane i ograniczenia

- Konta, kategorie i subskrypcje są zapisywane lokalnie w przeglądarce na danym urządzeniu. Nie są synchronizowane między przeglądarkami ani użytkownikami.
- Logowanie w tej wersji służy wyłącznie do rozdzielenia danych lokalnych. GitHub Pages nie zapewnia backendu, więc nie używaj tu prawdziwych haseł ani poufnych danych.
- Eksportuj JSON, aby wykonać kopię zapasową lub przenieść subskrypcje. Import JSON wczyta je do aktualnego konta w przeglądarce.
- Raport pokazuje bieżące aktywne subskrypcje. Historia płatności i raport PDF generowany przez serwer Pythona są dostępne tylko w wersji XAMPP; w GitHub Pages raport można wydrukować lub zapisać jako PDF z przeglądarki.

## Wersja XAMPP

`index.php`, `api.php` i `db.php` pozostają wersją serwerową korzystającą z PHP oraz MySQL. Instrukcje modułu raportów znajdują się w [raporty/README.md](raporty/README.md).
