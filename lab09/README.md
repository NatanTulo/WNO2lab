# Lab09 – Przetwarzanie Obrazów Narzędzi (OpenCV)

## Polecenie
1. Wczytanie obrazów przy użyciu modułów `os`, `sys`, `glob` (1 pkt)
2. Usunięcie tła za pomocą klasycznych metod przetwarzania obrazu (bez sieci neuronowych) (1 pkt)
3. Obrót obiektu tak, aby ostrze / szczęki były pionowo, uchwyt skierowany w dół (2 pkt)
4. Przycięcie i przeskalowanie do wspólnego formatu (1 pkt)
5. (*Opcjonalnie*) Pobranie 10 kolejnych obrazów z Google Images (+2 pkt)

## Implementacja
- Skrypt `main.py`:
  - Obsługa trybu lokalnego (`python main.py <folder>`) oraz pobierania: `python main.py google:<zapytanie>`
  - Pobieranie obrazów z użyciem `icrawler` (GoogleImageCrawler)
  - Konwersja do RGBA, detekcja obiektu:
    - Jeśli jest kanał alfa → maska z alfa
    - W przeciwnym razie adaptacyjne progowanie + morfologia
  - Wybór największego konturu → maska → wycięcie obiektu
  - Rotacja poprzez `minAreaRect` + korekta (uchwyt do dołu)
  - Czyszczenie tła (kanał alfa)
  - Zapis znormalizowanych (przyciętych) obrazów do `out/<nazwa_folderu_wejściowego>/`

## Wymagania
`opencv-python`, `numpy`, `Pillow`, `icrawler`.

## Instrukcje uruchomienia
1. (Opcjonalnie) utwórz środowisko wirtualne.
2. Zainstaluj zależności:
   ```
   pip install opencv-python numpy Pillow icrawler
   ```
3. Przetwarzanie istniejącego zestawu:
   ```
   python main.py in/komb
   ```
4. Pobieranie z Google i przetwarzanie:
   ```
   python main.py google:miecz
   ```
5. Wyniki w katalogu `out/<nazwa>`.

## Status realizacji
| Funkcjonalność | Punkty | Status |
|----------------|--------|--------|
| Wczytywanie obrazów (`os/sys/glob`) | 1 | ✅ |
| Usuwanie tła (progowanie / maska) | 1 | ✅ |
| Obrót + standaryzacja orientacji | 2 | ✅ |
| Przycięcie | 1 (część „przycięcie i przeskalowanie”) | ✅ (przycięcie) |
| Przeskalowanie do jednolitego rozmiaru | – | ❌ (parametr `size` nieużyty) |
| Pobieranie 10 obrazów (Google) | *2 | ✅ |

## Uwagi
- Można dodać końcową normalizację rozmiaru: `cv2.resize(rgba, size, interpolation=cv2.INTER_AREA)`.
- Rotacja korzysta z heurystyki (podział maski 50/50) – dla nietypowych kształtów może wymagać doprecyzowania (np. PCA + detekcja węższej części).
