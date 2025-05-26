# NER API (Named Entity Recognition) na CPU

Projekt implementuje prostą usługę NER (rozpoznawanie bytów nazwanych) działającą na CPU przy użyciu biblioteki `transformers`, udostępnioną jako API (Flask).

## Zawartość katalogu

- **app.py**  
  Serwer Flask z endpointami:
  - `GET /health` – sprawdzenie stanu (załadowany model).  
  - `GET /` – opis API.  
  - `POST /ner` – przyjmuje JSON `{ "text": "..." }`, zwraca listę bytów.

- **ner_model.py**  
  Klasa `NERProcessor` ładująca model NER na CPU oraz funkcje pomocnicze:
  - `load_ner_model()`  
  - `recognize_named_entities(text, processor)`

- **requirements.txt**  
  Wszystkie zależności Pythona.

- **Dockerfile**  
  Obraz oparty o `python:3.11-slim`, instalacja zależności i uruchomienie serwera za pomocą Gunicorna.

- **docker-compose.yml**  
  Konfiguracja usługi `ner-api` z mapowaniem portu, healthcheck i cache modeli.

- **run_server.py**  
  Skrypt uruchamiający aplikację lokalnie (Flask) z inicjalizacją modelu.

- **run_docker.sh**  
  Helper Bash do budowania, uruchamiania i kontroli kontenera Docker.

- **build_and_run.sh**  
  Prosty skrypt do ręcznego budowania obrazu i uruchamiania kontenera Docker.

- **test_api.py**  
  Testy funkcjonalne endpointu `/ner` i `/health` przy użyciu biblioteki `requests`.

- **test_docker_api.sh**  
  Skrypty Bash do testowania API uruchomionego w kontenerze Docker.

- **example_usage.py**  
  Przykład użycia funkcji NER z konsoli (uruchamiany jako skrypt).

## Wymagania

- Docker (do uruchamiania kontenera)
- Python 3.11 (do lokalnego uruchomienia)
- połączenie internetowe (pierwsze pobranie modelu z HuggingFace)

## Instalacja lokalna

1. Utworzyć i aktywować wirtualne środowisko:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Zainstalować zależności:
   ```bash
   pip install -r requirements.txt
   ```
3. Uruchomić serwer:
   ```bash
   python run_server.py
   ```
4. Sprawdzić:
   - `http://localhost:5000/health`
   - `http://localhost:5000/ner` (POST JSON)

## Uruchomienie w Dockerze

1. Budowa i uruchomienie (skrypt lub ręcznie):
   ```bash
   ./run_docker.sh run
   ```
   lub
   ```bash
   docker-compose up --build -d
   ```
2. API pod adresem `http://localhost:5000`

## Testowanie

- Lokalnie (po uruchomieniu serwera):
  ```bash
  python test_api.py
  ```
- W kontenerze:
  ```bash
  ./test_docker_api.sh
  ```

## Uwagi

- Maksymalna długość tekstu: 10000 znaków.
- Model działa wyłącznie na CPU (device=-1).

