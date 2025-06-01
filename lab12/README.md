# NER API - Named Entity Recognition

## Opis projektu

Aplikacja do rozpoznawania bytów nazwanych (Named Entity Recognition) z wykorzystaniem modelu BERT. API pozwala na analizę tekstu i identyfikację bytów takich jak osoby, organizacje, lokalizacje, etc.

## Struktura projektu

```
lab12/
├── README.md              # Dokumentacja projektu
├── app.py                 # Główna aplikacja Flask
├── ner_model.py           # Moduł do ładowania i użycia modelu NER
├── requirements.txt       # Zależności Python
├── Dockerfile            # Definicja obrazu Docker
├── run_docker.sh         # Skrypt do zarządzania kontenerem
└── test_docker_api.sh    # Skrypt do testowania API
```

## Rozwiązanie zadań

### 1. Model NER działający na CPU (1 pkt)

**Plik:** `ner_model.py`

Funkcja `recognize_named_entities()` przyjmuje tekst i zwraca listę słowników z rozpoznanymi bytami:

```python
from ner_model import recognize_named_entities

# Przykład użycia
text = "John Smith works at Microsoft Corporation in Seattle."
entities = recognize_named_entities(text)

# Wynik:
# [
#   {"text": "John Smith", "label": "PER", "confidence": 0.99, "start": 0, "end": 10},
#   {"text": "Microsoft Corporation", "label": "ORG", "confidence": 0.95, "start": 20, "end": 41},
#   {"text": "Seattle", "label": "LOC", "confidence": 0.98, "start": 45, "end": 52}
# ]
```

### 2. Aplikacja Flask z endpointem POST /ner (1 pkt)

**Plik:** `app.py`

API zawiera następujące endpointy:
- `POST /ner` - główny endpoint do analizy tekstu
- `GET /health` - sprawdzenie stanu aplikacji
- `GET /` - dokumentacja API

### 3. Requirements.txt i Dockerfile (1 pkt)

**Pliki:** `requirements.txt`, `Dockerfile`

- Dockerfile buduje obraz z modelem NER na CPU
- Requirements.txt zawiera wszystkie potrzebne zależności
- Obraz jest zoptymalizowany pod kątem rozmiaru i bezpieczeństwa

### 4. Uruchomienie z Dockera z mapowaniem portu (1 pkt)

Aplikacja jest dostępna na porcie 5000 z automatycznym mapowaniem.

## Instrukcja uruchomienia

### Opcja 1: Automatyczny skrypt (ZALECANE)

```bash
# Nadanie uprawnień wykonywania
chmod +x run_docker.sh

# Zbudowanie i uruchomienie kontenera
./run_docker.sh

# Inne opcje:
./run_docker.sh build     # Tylko budowa obrazu
./run_docker.sh stop      # Zatrzymanie kontenera
./run_docker.sh logs      # Wyświetlenie logów
./run_docker.sh status    # Sprawdzenie statusu
./run_docker.sh clean     # Usunięcie kontenera i obrazu
```

### Opcja 2: Ręczne polecenia Docker

```bash
# Budowanie obrazu
docker build -t ner-api .

# Uruchomienie kontenera z mapowaniem portu
docker run -d --name ner-api-container -p 5000:5000 ner-api

# Sprawdzenie statusu
docker ps

# Zatrzymanie
docker stop ner-api-container
```

## Testowanie API

### Automatyczne testy

```bash
# Nadanie uprawnień
chmod +x test_docker_api.sh

# Uruchomienie testów
./test_docker_api.sh
```

### Ręczne testowanie

```bash
# Sprawdzenie zdrowia aplikacji
curl http://localhost:5000/health

# Test rozpoznawania bytów
curl -X POST http://localhost:5000/ner \
  -H "Content-Type: application/json" \
  -d '{"text": "Donald Trump met with Vladimir Putin in Moscow."}'

# Dokumentacja API
curl http://localhost:5000/
```

## Endpointy API

### POST /ner

Rozpoznaje byty nazwane w tekście.

**Request:**
```json
{
  "text": "John Smith works at Microsoft Corporation in Seattle."
}
```

**Response:**
```json
{
  "success": true,
  "text": "John Smith works at Microsoft Corporation in Seattle.",
  "entities": [
    {
      "text": "John Smith",
      "label": "PER",
      "confidence": 0.9998,
      "start": 0,
      "end": 10
    },
    {
      "text": "Microsoft Corporation",
      "label": "ORG",
      "confidence": 0.9995,
      "start": 20,
      "end": 41
    },
    {
      "text": "Seattle",
      "label": "LOC",
      "confidence": 0.9999,
      "start": 45,
      "end": 52
    }
  ],
  "entities_count": 3
}
```

### GET /health

Sprawdza stan aplikacji.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

### GET /

Wyświetla dokumentację API w przeglądarce.

## Dostępne linki

Po uruchomieniu aplikacja jest dostępna pod:

- **API Dokumentacja:** http://localhost:5000
- **Health Check:** http://localhost:5000/health
- **NER Endpoint:** http://localhost:5000/ner (POST)

## Typy rozpoznawanych bytów

- **PER** - Osoby (np. John Smith, Anna Kowalska)
- **ORG** - Organizacje (np. Microsoft, Google)
- **LOC** - Lokalizacje (np. Seattle, Warsaw)
- **MISC** - Różne inne byty

## Wymagania systemowe

- Docker
- 2GB RAM (zalecane)
- Połączenie internetowe (do pobrania modelu przy pierwszym uruchomieniu)

## Rozwiązywanie problemów

### Kontener nie startuje
```bash
# Sprawdź logi
./run_docker.sh logs

# Lub
docker logs ner-api-container
```

### Model się nie ładuje
Model jest pobierany automatycznie przy pierwszym uruchomieniu. Może to zająć kilka minut.

### Port 5000 zajęty
```bash
# Zmień port w run_docker.sh lub użyj:
docker run -d --name ner-api-container -p 8080:5000 ner-api
```

## Przykłady użycia

### Python
```python
import requests

response = requests.post(
    'http://localhost:5000/ner',
    json={'text': 'Barack Obama was the President of the United States.'}
)
print(response.json())
```

### JavaScript
```javascript
fetch('http://localhost:5000/ner', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        text: 'Apple Inc. is located in Cupertino, California.'
    })
})
.then(response => response.json())
.then(data => console.log(data));
```

### cURL
```bash
curl -X POST http://localhost:5000/ner \
  -H "Content-Type: application/json" \
  -d '{"text": "Elon Musk founded Tesla Motors."}'
```