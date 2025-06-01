from flask import Flask, request, jsonify, render_template_string
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
        return True
    except Exception as e:
        logger.error(f"Błąd podczas ładowania modelu NER: {e}", exc_info=True)
        ner_processor = None
        return False

def get_or_load_ner_processor():
    """Lazy loading modelu NER - ładuje tylko przy pierwszym użyciu."""
    global ner_processor
    if ner_processor is None:
        logger.info("Ładowanie modelu NER przy pierwszym użyciu...")
        try:
            # Dodatkowe logowanie dla debugowania
            import os
            logger.info(f"Katalog roboczy: {os.getcwd()}")
            logger.info(f"Zawartość katalogu: {os.listdir('.')}")
            logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'brak')}")
            
            ner_processor = load_ner_model()
            logger.info("Model NER załadowany pomyślnie!")
        except Exception as e:
            logger.error(f"Błąd podczas ładowania modelu NER: {e}", exc_info=True)
            # Dodatkowe informacje o błędzie
            import traceback
            logger.error(f"Pełny traceback: {traceback.format_exc()}")
            ner_processor = None
    return ner_processor

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint do sprawdzania stanu aplikacji."""
    # Sprawdzamy czy model można załadować
    processor = get_or_load_ner_processor()
    status = "healthy" if processor is not None else "unhealthy"
    return jsonify({
        "status": status,
        "model_loaded": processor is not None
    })

@app.route('/ner', methods=['POST'])
def extract_entities():
    """
    Endpoint do rozpoznawania bytów nazwanych w tekście.
    
    Oczekuje JSON: {"text": "tekst do analizy"}
    Zwraca JSON z rozpoznanymi bytami.
    """
    try:
        # Sprawdzenie czy model można załadować
        processor = get_or_load_ner_processor()
        if processor is None:
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
            entities = recognize_named_entities(text, processor)
            
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

@app.route('/debug', methods=['GET'])
def debug_info():
    """Endpoint do debugowania - pokazuje szczegółowe informacje."""
    try:
        import os
        import sys
        
        debug_data = {
            "working_directory": os.getcwd(),
            "directory_contents": os.listdir('.'),
            "python_path": sys.path,
            "environment_vars": {
                "PYTHONPATH": os.environ.get('PYTHONPATH', 'brak'),
                "TRANSFORMERS_CACHE": os.environ.get('TRANSFORMERS_CACHE', 'brak')
            }
        }
        
        # Próba załadowania modelu z pełnym traceback
        try:
            from ner_model import load_ner_model
            processor = load_ner_model()
            debug_data["model_loading"] = "SUCCESS"
        except Exception as e:
            import traceback
            debug_data["model_loading"] = "FAILED"
            debug_data["error"] = str(e)
            debug_data["traceback"] = traceback.format_exc()
        
        return jsonify(debug_data)
        
    except Exception as e:
        return jsonify({"debug_error": str(e)})

@app.route('/', methods=['GET'])
def index():
    """Strona główna z dokumentacją API w formacie HTML."""
    
    # Sprawdzamy czy request pochodzi z przeglądarki
    user_agent = request.headers.get('User-Agent', '').lower()
    accept_header = request.headers.get('Accept', '')
    
    # Jeśli to przeglądarka, wyświetl HTML
    if 'mozilla' in user_agent or 'text/html' in accept_header:
        html_template = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NER API - Dokumentacja</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; line-height: 1.6; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .endpoint { background: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 15px 0; border-radius: 4px; }
        .method { background: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
        .method.get { background: #007bff; }
        .method.post { background: #28a745; }
        code { background: #f1f1f1; padding: 2px 4px; border-radius: 3px; font-family: monospace; }
        pre { background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto; border: 1px solid #e9ecef; }
        .example { background: #fff3cd; border: 1px solid #ffeeba; padding: 15px; border-radius: 4px; margin: 10px 0; }
        .status { display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
        .status.healthy { background: #d4edda; color: #155724; }
        .status.loading { background: #fff3cd; color: #856404; }
        h1, h2, h3 { color: #2c3e50; }
        .test-form { background: #e9ecef; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .form-group { margin: 15px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        textarea, input { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .result { margin-top: 15px; padding: 15px; border-radius: 4px; background: #f8f9fa; border: 1px solid #e9ecef; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 NER API - Named Entity Recognition</h1>
        <p>API do rozpoznawania bytów nazwanych przy użyciu modelu BERT</p>
        <div>Status: <span id="status" class="status loading">Sprawdzanie...</span></div>
    </div>

    <h2>📋 Dostępne endpointy</h2>

    <div class="endpoint">
        <h3><span class="method post">POST</span> /ner</h3>
        <p><strong>Opis:</strong> Rozpoznaje byty nazwane w podanym tekście</p>
        <p><strong>Content-Type:</strong> application/json</p>
        
        <h4>Przykład request:</h4>
        <pre><code>{
  "text": "Donald Trump spotkał się z Vladimirem Putinem w Moskwie."
}</code></pre>

        <h4>Przykład response:</h4>
        <pre><code>{
  "success": true,
  "text": "Donald Trump spotkał się z Vladimirem Putinem w Moskwie.",
  "entities": [
    {
      "text": "Donald Trump",
      "label": "PER",
      "confidence": 0.9998,
      "start": 0,
      "end": 12
    },
    {
      "text": "Vladimirem Putinem",
      "label": "PER", 
      "confidence": 0.9995,
      "start": 25,
      "end": 43
    }
  ],
  "entities_count": 2
}</code></pre>
    </div>

    <div class="endpoint">
        <h3><span class="method get">GET</span> /health</h3>
        <p><strong>Opis:</strong> Sprawdza stan aplikacji i czy model jest załadowany</p>
        
        <h4>Przykład response:</h4>
        <pre><code>{
  "status": "healthy",
  "model_loaded": true
}</code></pre>
    </div>

    <div class="endpoint">
        <h3><span class="method get">GET</span> /</h3>
        <p><strong>Opis:</strong> Wyświetla tę dokumentację (HTML) lub informacje o API (JSON)</p>
    </div>

    <h2>🧪 Testowanie API</h2>
    
    <div class="test-form">
        <h3>Przetestuj rozpoznawanie bytów</h3>
        <div class="form-group">
            <label for="testText">Tekst do analizy:</label>
            <textarea id="testText" rows="4" placeholder="Wprowadź tekst do analizy, np: John Smith pracuje w Microsoft Corporation w Seattle.">John Smith pracuje w Microsoft Corporation w Seattle.</textarea>
        </div>
        <button onclick="testNER()">Analizuj tekst</button>
        <div id="result" class="result" style="display:none;"></div>
    </div>

    <h2>📖 Typy rozpoznawanych bytów</h2>
    <ul>
        <li><strong>PER</strong> - Osoby (np. John Smith, Anna Kowalska)</li>
        <li><strong>ORG</strong> - Organizacje (np. Microsoft, Google)</li>
        <li><strong>LOC</strong> - Lokalizacje (np. Seattle, Warszawa)</li>
        <li><strong>MISC</strong> - Różne inne byty</li>
    </ul>

    <h2>🛠️ Przykłady użycia</h2>

    <div class="example">
        <h4>cURL:</h4>
        <pre><code>curl -X POST http://localhost:5000/ner \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Elon Musk założył firmę Tesla Motors."}'</code></pre>
    </div>

    <div class="example">
        <h4>Python:</h4>
        <pre><code>import requests

response = requests.post(
    'http://localhost:5000/ner',
    json={'text': 'Barack Obama był Prezydentem Stanów Zjednoczonych.'}
)
print(response.json())</code></pre>
    </div>

    <div class="example">
        <h4>JavaScript:</h4>
        <pre><code>fetch('http://localhost:5000/ner', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        text: 'Apple Inc. ma siedzibę w Cupertino w Kalifornii.'
    })
})
.then(response => response.json())
.then(data => console.log(data));</code></pre>
    </div>

    <script>
        // Sprawdzenie stanu aplikacji
        fetch('/health')
            .then(response => response.json())
            .then(data => {
                const statusEl = document.getElementById('status');
                if (data.status === 'healthy' && data.model_loaded) {
                    statusEl.textContent = 'Aplikacja działa poprawnie';
                    statusEl.className = 'status healthy';
                } else {
                    statusEl.textContent = 'Problemy z aplikacją';
                    statusEl.className = 'status loading';
                }
            })
            .catch(() => {
                const statusEl = document.getElementById('status');
                statusEl.textContent = 'Brak połączenia';
                statusEl.className = 'status loading';
            });

        // Funkcja testowania NER
        function testNER() {
            const text = document.getElementById('testText').value;
            const resultDiv = document.getElementById('result');
            
            if (!text.trim()) {
                alert('Wprowadź tekst do analizy');
                return;
            }

            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<p>Analizowanie tekstu...</p>';

            fetch('/ner', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: text})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    let html = '<h4>Wyniki analizy:</h4>';
                    html += `<p><strong>Znaleziono bytów:</strong> ${data.entities_count}</p>`;
                    
                    if (data.entities.length > 0) {
                        html += '<ul>';
                        data.entities.forEach(entity => {
                            html += `<li><strong>${entity.text}</strong> (${entity.label}) - pewność: ${(entity.confidence * 100).toFixed(1)}%</li>`;
                        });
                        html += '</ul>';
                    } else {
                        html += '<p>Nie znaleziono żadnych bytów nazwanych.</p>';
                    }
                    
                    html += '<h4>Pełna odpowiedź JSON:</h4>';
                    html += `<pre><code>${JSON.stringify(data, null, 2)}</code></pre>`;
                } else {
                    html = `<h4>Błąd:</h4><p>${data.error}</p><p>${data.message}</p>`;
                }
                resultDiv.innerHTML = html;
            })
            .catch(error => {
                resultDiv.innerHTML = `<h4>Błąd połączenia:</h4><p>${error.message}</p>`;
            });
        }
    </script>
</body>
</html>
        """
        return render_template_string(html_template)
    
    # Dla API clients (curl, etc.) zwróć JSON
    else:
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
    success = initialize_ner_model()
    if not success:
        logger.error("Nie udało się załadować modelu NER!")
    
    # Uruchomienie aplikacji
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
