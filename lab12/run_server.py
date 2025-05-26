from app import app, initialize_ner_model
import logging

def main():
    """Uruchamia serwer Flask z inicjalizacją modelu."""
    
    # Konfiguracja logowania
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=== NER API Server ===")
    print("Inicjalizacja modelu NER...")
    
    # Inicjalizacja modelu
    initialize_ner_model()
    
    print("Uruchamianie serwera...")
    print("API dostępne pod adresem: http://localhost:5000")
    print("Dokumentacja: http://localhost:5000")
    print("Health check: http://localhost:5000/health")
    print("Endpoint NER: POST http://localhost:5000/ner")
    print("\nAby zatrzymać serwer, naciśnij Ctrl+C")
    
    # Uruchomienie serwera
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False  # Wyłączenie debug w trybie produkcyjnym
    )

if __name__ == '__main__':
    main()
