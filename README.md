# Laboratoria WNO2

Repozytorium zawiera zestaw laboratoriów z obszarów sieci, poczty elektronicznej, tworzenia silnika gry, przetwarzania obrazu, detekcji obiektów, audio oraz MLOps / Docker.

## Zawartość
- **Lab01 (TCP/IP Chat):** Asynchroniczna komunikacja wielu klientów (wątki), szyfrowanie (Caesar), prywatne wiadomości, wysyłanie plików audio.
- **Lab02 (SMTP/IMAP/POP3 Klient):** Graficzny klient poczty (PyQt5) z obsługą wysyłania, odbioru, załączników, autorespondera i analizy sentymentu.
- **Lab03-06 (Silnik Gry / Historia / Config):** Strategiczna gra turowa (Cell Expansion Wars) z AI (MCTS), zapisem historii (JSON / XML / MongoDB), quicksave / replay, edytorem poziomów.
- **Lab09 (OpenCV – Obróbka Narzędzi):** Usuwanie tła, wyrównanie i normalizacja orientacji narzędzi, pobieranie obrazów z Google.
- **Lab10 (Detekcja Obiektów YOLO + XAI):** Generacja syntetycznego datasetu, trening YOLO, test pipeline, CAM / Grad-CAM wizualizacje.
- **Lab11 (Audio):** Speech-to-Text (Whisper), Text-to-Speech, analiza jakości nagrań, wyszukiwanie słów kluczowych.
- **Lab12 (Docker + NER API):** API Flask / FastAPI dla NER (BERT), konteneryzacja w Docker, testy endpointów.

## Instalacja zależności
Każde laboratorium posiada własny plik `requirements.txt` lub sekcję README z wymaganiami. Zaleca się tworzyć osobne wirtualne środowiska dla większych projektów (np. gry, YOLO, Docker/NER).

Przykład (Windows / PowerShell):
```
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

## Uruchamianie
- Szczegółowe instrukcje znajdują się w README poszczególnych folderów.
- Laboratoria są niezależne – można je uruchamiać osobno.

## Technologie (przegląd)
- Sieci / Sockety: `socket`, `threading`
- Poczta: `smtplib`, `imaplib`, `poplib`, `email`, `PyQt5`, `textblob`
- GUI / Gra: `PyQt5`, struktury scen / obiektów, MCTS (AI)
- Przetwarzanie obrazu: `opencv-python`, `numpy`, `Pillow`, `icrawler`
- Detekcja obiektów: `ultralytics` (YOLO), `torch`, CAM / wizualizacja
- Audio: `whisper`, `librosa`, `pyttsx3`
- NLP / MLOps: `transformers`, `Flask`/`FastAPI`, `Docker`

## Status
Szczegółowe tabele punktów oraz stopień realizacji funkcji znajdują się w README danego laboratorium (tam gdzie wymagane przez polecenia). Brakujące moduły opcjonalne są oznaczone jako niewykonane, bez wpływu na działanie podstawowych funkcji.

## Struktura (wycinek)
```
WNO2lab/
  lab01/  # TCP/IP Chat
  lab02/  # Klient pocztowy + autoresponder
  lab03/  # Silnik gry + AI
  lab09/  # Obróbka narzędzi (OpenCV)
  lab10/  # YOLO + XAI
  lab11/  # Audio STT/TTS/analiza
  lab12/  # NER API + Docker
```

## Uwagi
- Laboratoria 3–6 są scalone tematycznie w ramach jednego projektu gry.
- Część zadań rozszerzających (np. widok 3D, sterowanie gestami) pozostaje niewykonanych – opisane w tabelach.

---
Dokument uzupełnia istniejące szczegółowe README – w razie rozbudowy kolejnych modułów należy dodać je do sekcji "Zawartość".
