# Lab01 – Asynchroniczny Chat TCP/IP

## Polecenie
Napisać dwa skrypty (serwer i klient) komunikujące się asynchronicznie po `localhost`:
- Skrypt serwera oraz klienta (1 pkt)
- Użycie wątków (1 pkt)
- Komunikacja asynchroniczna (wielu nadawców bez blokowania) (3 pkt)

Rozszerzenia (Grupa 2 – 10:15):
- Szyfrowanie i deszyfrowanie wiadomości (1* pkt)
- Obsługa wielu klientów w czasie rzeczywistym (1* pkt)
- Wysyłanie i odbiór plików audio (1* pkt)
- Automatyczne ponawianie przerwanego połączenia (1* pkt) – NIE zrealizowano

Rozszerzenia (Grupa 1 – 7:15) – NIEWYMAGANE w tej wersji:
- ASCII-art z obrazu, przesył *.docx, nieograniczona liczba klientów, GUI PySide2/6

## Wymagania
Standardowa biblioteka Pythona (`socket`, `threading`, `os`). Brak dodatkowych zależności.

## Instrukcje uruchomienia
1. Uruchom serwer w pierwszej konsoli:
   ```
   python lab_server.py
   ```
2. Uruchom jedną lub więcej instancji klienta w osobnych konsolach:
   ```
   python lab_client.py
   ```
3. Komendy klienta:
   - Zwykła wiadomość: wpisz tekst i ENTER
   - Zmiana nicku: `/nick <nowa_nazwa>`
   - Prywatna wiadomość: `/me <nick_adresata> <treść>`
   - Wysłanie pliku audio: `/send <ścieżka_do_pliku>`

## Mechanizmy
- Szyfrowanie uproszczonym szyfrem Cezara (`SHIFT=1`) – pełny obieg (encrypt + decrypt)
- Broadcast z wykluczeniem nadawcy
- Prywatne wiadomości przez prefiks `PRIVATE|`
- Transfer pliku audio z nagłówkiem `AUDIO|nazwa|rozmiar` i strumieniowym dosyłaniem

## Status realizacji
| Funkcjonalność | Punkty | Status |
|----------------|--------|--------|
| Skrypt serwera i klienta | 1 | ✅ |
| Wątki (obsługa klientów + wejście serwera) | 1 | ✅ |
| Asynchroniczna komunikacja (brak blokowania wejścia) | 3 | ✅ |
| Szyfrowanie / deszyfrowanie (gr.2) | 1* | ✅ |
| Wielu klientów jednocześnie (gr.2) | 1* | ✅ |
| Wysyłanie / odbiór audio (gr.2) | 1* | ✅ |
| Automatyczne ponawianie połączenia (gr.2) | 1* | ❌ |
| GUI / ASCII / DOCX (gr.1 dodatkowe) | * | ❌ (nie dotyczy) |

## Uwagi
- Reconnect można dodać poprzez pętlę z próbą `connect()` + timeout.
- Szyfrowanie jest symboliczne – możliwa przyszła wymiana na np. AES (PyCryptodome).
