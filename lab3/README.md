# Cell Expansion Wars

Strategiczna gra turowa, w której twoim celem jest dominacja nad planszą poprzez zarządzanie komórkami, tworzenie połączeń i przejmowanie komórek przeciwnika.

## Wymagania

- Python 3.6+
- PyQt5

## Instalacja

1. Wypakuj repozytorium.
2. Zainstaluj wymagane zależności:
   ```
   pip install -r requirements.txt
   ```

## Uruchomienie gry

```
python main.py
```

## Sterowanie

- **Lewy przycisk myszy**: Wybór komórki gracza i tworzenie połączeń
- **Prawy przycisk myszy**: W trybie developerskim - sterowanie komórkami przeciwnika
- **Klawisz H**: Pokaż podpowiedź strategiczną
- **Klawisz I**: Pokaż informacje o wybranej komórce/moście
- **Klawisz ESC**: Powrót do menu

## Zasady gry

1. Zdobywaj punkty, które zwiększają siłę twoich komórek.
2. Twórz mosty między komórkami, aby przesyłać punkty.
3. Przejmuj neutralne i wrogie komórki.
4. Wygrywa ten, kto wyeliminuje wszystkie komórki przeciwnika.

## Funkcjonalności i ocena

Projekt zrealizowany w ramach laboratorium, zaimplementowane funkcjonalności:

| Funkcjonalność | Punkty | Status | Implementacja (liczba przy pliku oznacza numer linijki w danym pliku)|
|----------------|--------|--------|--------|
| QGraphicsScene – implementacja sceny gry | 1 pkt | ✅ | game_scene.py |
| Dziedziczenie po QGraphicsItem – jednostki jako osobne obiekty | 1 pkt | ✅ | game_objects.py |
| Interaktywność jednostek – klikalność, przeciąganie, menu kontekstowe | 3 pkt | ✅ | 224-507 game_scene.py, 788-830 game_scene.py |
| Sterowanie jednostkami – wybór z menu i ruch na siatce planszy | 2 pkt | ✅ | level_editor_scene.py - w grze moim zdaniem mechanika ruchu jednostek po planszy nie ma sensu, bo by to niszczyło ekonomię gry, więc zrobiłem edytor poziomów, który implementuje takie zachowanie poza rozgrywką - poziomy się nadpisują do pliku JSON, a następnie można je wczytać uruchamiając dany poziom |
| Zaciąganie grafik jednostek z pliku .rc  | 1 pkt | ✅ | plik "resources.rc" + komenda "pyrcc5 resources.rc -o resources_rc.py" daje resources_rc.py, 147 menu_scene.py - uznałem że jednostki można na tyle ładnie tworzyć programowo bez pomocy tekstur, że żeby zastosować ten plik stworzę ikonkę w menu do edytora poziomów |
| Podświetlanie możliwych ruchów i ataków w zależności od mnożnika | 2 pkt | ✅ | 59-62 game_objects.py oraz metoda pomocnicza setHighlighted 26-30 game_objects.py używana kilkukrotnie w game_scene.py |
| System walki uwzględniający poziomy, mnożenie jednostek i specjalne efekty bitewne  | 3 pkt | ✅ | 200, 392 game_scene.py - strength to poziom, można zbudować tyle mostów ile wynosi poziom danej komórki, mnożenie jednostek i specjalne efekty bitewne to powerupy dostępne w górnym pasku - 43-50 main.py, mechanika powerupów: 230-354 game_scene.py |
| Mechanizm tur i licznik czasu na wykonanie ruchu (zegar rundowy) | 2 pkt | ✅ | 853-874 game_scene.py - implementacja zegara rundowego, 486-490, 591-599 game_scene.py - możliwość ruchów graczy tylko podczas ich tur
| System podpowiedzi strategicznych oparty na AI (np. najlepszy ruch w turze) | 1 pkt | ✅ | game_ai.py - Monte-Carlo Tree Search, 753-771 game_scene.py - wyświetlanie podpowiedzi |
| Sterowanie jednostkami za pomocą gestów z kamery (kliknięcie ruchem dłoni) | 2 pkt | ❌ |
| Logger wyświetlający komunikaty na konsoli i w interfejsie QTextEdit z rotującym logowaniem | 1 pkt | ✅ | logger.py oraz zastosowanie w pozostałych plikach |
| Przełączanie widoku między 2D i 3D (w tym renderowanie jednostek w 3D) | 4 pkt | ❌ |
| **RAZEM** | **23 pkt** | **17/23** |