from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from typing import Dict, Any
from ner_model import recognize_named_entities, load_ner_model, NERProcessor

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicjalizacja aplikacji Flask
app = Flask(__name__)
CORS(app)  # Umożliwia CORS dla frontend aplikacji

# Globalna zmienna dla procesora NER
ner_processor: NERProcessor = None

def initialize_ner_model():
    """Inicjalizuje model NER przy starcie aplikacji."""
    global ner_processor
    try:
        logger.info("Inicjalizacja modelu NER...")
        ner_processor = load_ner_model()
        logger.info("Model NER załadowany pomyślnie!")
    except Exception as e:
        logger.error(f"Błąd podczas ładowania modelu NER: {e}")
        ner_processor = None

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint do sprawdzania stanu aplikacji."""
    status = "healthy" if ner_processor is not None else "unhealthy"
    return jsonify({
        "status": status,
        "model_loaded": ner_processor is not None
    })

@app.route('/ner', methods=['POST'])
def extract_entities():
    """
    Endpoint do rozpoznawania bytów nazwanych w tekście.
    
    Oczekuje JSON: {"text": "tekst do analizy"}
    Zwraca JSON z rozpoznanymi bytami.
    """
    try:
        # Sprawdzenie czy model jest załadowany
        if ner_processor is None:
            return jsonify({
                "error": "Model NER nie jest dostępny",
                "message": "Spróbuj ponownie później lub skontaktuj się z administratorem"
            }), 503
        
        # Sprawdzenie czy request zawiera JSON
        if not request.is_json:
            return jsonify({
                "error": "Nieprawidłowy format danych",
                "message": "Oczekiwany format JSON"
            }), 400
        
        data = request.get_json()
        
        # Walidacja danych wejściowych
        if not data or 'text' not in data:
            return jsonify({
                "error": "Brak wymaganego pola 'text'",
                "message": "Wyślij JSON z polem 'text' zawierającym tekst do analizy"
            }), 400
        
        text = data['text']
        
        # Sprawdzenie czy tekst nie jest pusty
        if not text or not text.strip():
            return jsonify({
                "error": "Pusty tekst",
                "message": "Pole 'text' nie może być puste"
            }), 400
        
        # Ograniczenie długości tekstu (zabezpieczenie przed zbyt długimi tekstami)
        if len(text) > 10000:
            return jsonify({
                "error": "Tekst zbyt długi",
                "message": "Maksymalna długość tekstu to 10000 znaków"
            }), 400
        
        # Rozpoznawanie bytów nazwanych
        logger.info(f"Przetwarzanie tekstu o długości {len(text)} znaków")
        try:
            entities = recognize_named_entities(text, ner_processor)
            
            # Konwersja numpy float32 na Python float dla JSON serialization
            for entity in entities:
                if 'confidence' in entity:
                    entity['confidence'] = float(entity['confidence'])
                    
        except Exception as ner_error:
            logger.error(f"Błąd w recognize_named_entities: {ner_error}", exc_info=True)
            raise ner_error
        
        # Przygotowanie odpowiedzi
        response = {
            "success": True,
            "text": text,
            "entities": entities,
            "entities_count": len(entities)
        }
        
        logger.info(f"Znaleziono {len(entities)} bytów nazwanych")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania: {e}", exc_info=True)
        return jsonify({
            "error": "Błąd wewnętrzny serwera",
            "message": "Wystąpił nieoczekiwany błąd podczas przetwarzania tekstu",
            "debug_info": str(e) if app.debug else None
        }), 500

@app.route('/', methods=['GET'])
def index():
    """Strona główna z informacjami o API."""
    return jsonify({
        "name": "NER API",
        "version": "1.0.0",
        "description": "API do rozpoznawania bytów nazwanych (Named Entity Recognition)",
        "endpoints": {
            "POST /ner": "Rozpoznaje byty nazwane w tekście",
            "GET /health": "Sprawdza stan aplikacji",
            "GET /": "Informacje o API"
        },
        "usage": {
            "endpoint": "/ner",
            "method": "POST",
            "content_type": "application/json",
            "body": {"text": "Tekst do analizy"},
            "example": {
                "request": {"text": "John Smith works at Microsoft in Seattle."},
                "response": {
                    "success": True,
                    "entities": [
                        {"text": "John Smith", "label": "PER", "confidence": 0.99},
                        {"text": "Microsoft", "label": "ORG", "confidence": 0.95}
                    ]
                }
            }
        }
    })

if __name__ == '__main__':
    # Inicjalizacja modelu przy starcie
    initialize_ner_model()
    
    # Uruchomienie aplikacji
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True  # Włączenie debug mode
    )
