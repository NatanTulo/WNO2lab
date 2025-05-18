# Cell Expansion Wars

Strategiczna gra turowa, w której twoim celem jest dominacja nad planszą poprzez zarządzanie komórkami, tworzenie połączeń i przejmowanie komórek przeciwnika.

## Wymagania

- Python 3.6+
- PyQt5
- pymongo

## Instalacja

1. Wypakuj repozytorium.
2. Zainstaluj wymagane zależności:
   ```
   pip install -r requirements.txt
   ```

## Konfiguracja MongoDB

Aby korzystać z funkcji zapisu historii gry w MongoDB, wykonaj następujące kroki:
1. Pobierz i zainstaluj MongoDB ze strony: https://www.mongodb.com/try/download/community
2. Uruchom serwer MongoDB, np. używając polecenia:
   ```
   mongod --dbpath <ścieżka_do_folderu_z_danymi>
   ```
   Domyślnie serwer nasłuchuje na porcie 27017.
3. Program używa bazy "wno2lab" oraz kolekcji "replays". W razie potrzeby zmień konfigurację w pliku game_history.py.

## Uruchomienie gry

```
python main.py
```

## Sterowanie

- **Lewy przycisk myszy**: Wybór komórki gracza i tworzenie połączeń
- **Prawy przycisk myszy**: W trybie developerskim - sterowanie komórkami przeciwnika
- **Klawisz H**: Pokaż podpowiedź strategiczną
- **Klawisz I**: Pokaż informacje o wybranej komórce/moście
- **Klawisz Q**: Wykonaj szybką grę (quicksave)
- **Klawisz L**: Wczytaj szybką grę (quickload)
- **Klawisz ESC**: Powrót do menu

## Zasady gry

1. Zdobywaj punkty, które zwiększają siłę twoich komórek.
2. Twórz mosty między komórkami, aby przesyłać punkty.
3. Przejmuj neutralne i wrogie komórki.
4. Wygrywa ten, kto wyeliminuje wszystkie komórki przeciwnika.

## Funkcjonalności i ocena

### Lab. 3-5. Silnik

Projekt zrealizowany w ramach laboratorium, zaimplementowane funkcjonalności:

| Funkcjonalność | Punkty | Status | Implementacja |
|----------------|--------|--------|----------------------------------------------------------------------|
| QGraphicsScene – implementacja sceny gry | 1 pkt | ✅ | game_scene.py |
| Dziedziczenie po QGraphicsItem – jednostki jako osobne obiekty | 1 pkt | ✅ | game_objects.py |
| Interaktywność jednostek – klikalność, przeciąganie, menu kontekstowe | 3 pkt | ✅ | game_scene.py |
| Sterowanie jednostkami – wybór z menu i ruch na siatce planszy | 2 pkt | ✅ | level_editor_scene.py - w grze moim zdaniem mechanika ruchu jednostek po planszy nie ma sensu, bo by to niszczyło ekonomię gry, więc zrobiłem edytor poziomów, który implementuje takie zachowanie poza rozgrywką - poziomy się nadpisują do pliku JSON, a następnie można je wczytać uruchamiając dany poziom |
| Zaciąganie grafik jednostek z pliku .rc  | 1 pkt | ✅ | plik "resources.rc" + komenda "pyrcc5 resources.rc -o resources_rc.py" daje resources_rc.py; menu_scene.py - uznałem że jednostki można na tyle ładnie tworzyć programowo bez pomocy tekstur, że żeby zastosować ten plik stworzę ikonkę w menu do edytora poziomów |
| Podświetlanie możliwych ruchów i ataków w zależności od mnożnika | 2 pkt | ✅ | game_objects.py oraz metoda pomocnicza setHighlighted używana kilkukrotnie w game_scene.py |
| System walki uwzględniający poziomy, mnożenie jednostek i specjalne efekty bitewne  | 3 pkt | ✅ | game_scene.py - strength to poziom, można zbudować tyle mostów ile wynosi poziom danej komórki, mnożenie jednostek i specjalne efekty bitewne to powerupy dostępne w górnym pasku - main.py, mechanika powerupów: game_scene.py |
| Mechanizm tur i licznik czasu na wykonanie ruchu (zegar rundowy) | 2 pkt | ✅ | game_scene.py - implementacja zegara rundowego, game_scene.py - możliwość ruchów graczy tylko podczas ich tur
| System podpowiedzi strategicznych oparty na AI (np. najlepszy ruch w turze) | 1 pkt | ✅ | game_ai.py - Monte-Carlo Tree Search, game_scene.py - wyświetlanie podpowiedzi |
| Sterowanie jednostkami za pomocą gestów z kamery (kliknięcie ruchem dłoni) | 2 pkt | ❌ |
| Logger wyświetlający komunikaty na konsoli i w interfejsie QTextEdit z rotującym logowaniem | 1 pkt | ✅ | logger.py oraz zastosowanie w pozostałych plikach |
| Przełączanie widoku między 2D i 3D (w tym renderowanie jednostek w 3D) | 4 pkt | ❌ |
| **RAZEM** | **23 pkt** | **17/23** |

### Lab. 6. Config & history
| Funkcjonalność | Punkty | Status | Implementacja |
|----------------|--------|--------|-----------------------------------------------------------------------|
| Tryb gry: 1 gracz / 2 graczy lokalnie / gra sieciowa (grupa radio buttons) | 0.5 pkt |✅| 1 gracz zaimplementowany przy pomocy MCTS z game_ai.py, 2 gracze lokalnie to wcześniejsza wersja rozgrywki - lpm = gracz, ppm = przeciwnik, gra sieciowa niezaimplementowana |
| Adres IP i port (line edit z maską, walidacją i podpowiedzią) | 0.5 pkt |✅| po wybraniu gry sieciowej pojawiają się pola tekstowe do wpisania adresu IP i portu - IP jest walidowany w każdym oktecie - nie da się wpisać innej wartości niż poprawna, port ma ograniczoną liczbę cyfr |
| Zapis i odczyt historii gry (XML) | 1 pkt |✅| quicksave oraz powtórka |
| Zapis i odczyt historii gry w bazie danych NoSQL (np. MongoDB lub Firebase) | 1 pkt |✅| MongoDB - quicksave oraz powtórka |
| Zapis i odczyt historii  gry (JSON) | 1 pkt |✅| quicksave oraz powtórka |
| Odczyt i playback zapisanej historii gry z kontrolą szybkości odtwarzania | 1 pkt |✅| prawidłowe odtwarzanie wszystkich ruchów z wybranej przez użytkownika powtórki, możliwość kontroli szybkości odtwarzania przy pomocy suwaka |
| **RAZEM** | **5 pkt** | **5/5** |