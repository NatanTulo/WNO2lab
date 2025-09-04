# Lab02 – Klient Poczty (SMTP / POP3 / IMAP) + Autoresponder

## Polecenie
Stworzyć graficznego klienta pocztowego (IMAP/POP3/SMTP):
- Odbieranie maili i ich wyświetlanie (1 pkt)
- Wysyłanie maili (1 pkt)
- Filtracja / inteligentna analiza słów (2 pkt)
- Autoresponder (1 pkt)

Wersja (Grupa 10:15) – alternatywne punktowanie:
- Odbiór + wysyłka + autoresponder (1 pkt)
- Inteligentna filtracja + analiza sentymentu (3 pkt)
- Wysyłanie z załącznikami (1 pkt)

Rozszerzenia opcjonalne:
- Potwierdzenie przeczytania (*2 pkt)
- Automatyczne tworzenie maila w globalnym serwisie (*1 pkt)

## Funkcje zaimplementowane
- GUI (PyQt5) z zakładkami: obsługa maili / autoresponder
- SMTP: wysyłanie wiadomości + załączniki + nagłówki żądania potwierdzenia odczytu (`Disposition-Notification-To`)
- POP3 / IMAP: paginowane pobieranie tematów + wyświetlanie treści wybranej wiadomości
- Analiza sentymentu tematów (TextBlob) – etykiety: Pozytywny / Neutralny / Negatywny
- Autoresponder w osobnym wątku: filtruje duplikaty, pomija automatyczne odpowiedzi, odpowiada tylko na nowe wiadomości (czas startu)
- Dynamiczne włączanie/wyłączanie autorespondera + logi (`autoresponder.log`)

## Wymagania
`PyQt5`, `textblob`, `smtplib` / `imaplib` / `poplib`, `email`, `ssl` (standard), ewentualnie model korpusu dla TextBlob (w razie potrzeby).

## Instrukcje uruchomienia
1. (Opcjonalnie) utwórz środowisko wirtualne.
2. Zainstaluj zależności (jeśli istnieje lokalny `requirements.txt`, uzupełnij go odpowiednimi pakietami):
   ```
   pip install pyqt5 textblob
   ```
3. Uruchom aplikację GUI:
   ```
   python gui.py
   ```
4. Wprowadź dane konta (dla Gmail: konieczne hasło aplikacji). 
5. W zakładce autoresponder ustaw treść i częstotliwość, zaznacz „Włącz autoresponder”.

## Status realizacji
| Funkcjonalność | Punkty | Status |
|----------------|--------|--------|
| Odbiór maili (POP3 / IMAP) | 1 | ✅ |
| Wysyłanie maili (SMTP) | 1 | ✅ |
| Analiza / filtracja (sentyment + proste reguły) | 2 / 3 | ✅ |
| Autoresponder (wątek + filtrowanie) | 1 | ✅ |
| Wysyłanie z załącznikami (gr. 10:15) | 1 | ✅ |
| Potwierdzenie przeczytania (*2) | * | ✅ (nagłówki) |
| Automatyczne tworzenie maila w globalnym serwisie (*1) | * | ❌ |

## Uwagi
- Potwierdzenie odczytu zależy od klienta odbiorcy – nie wszystkie zwracają MDN.
- Można dodać prostą klasyfikację tematów (np. TF-IDF + Naive Bayes) jako dalsze rozszerzenie.
