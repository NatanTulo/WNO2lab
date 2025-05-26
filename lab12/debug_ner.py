from ner_model import NERProcessor
import traceback

def debug_ner():
    """Debuguje problem z NER bezpośrednio."""
    
    print("=== Debug NER ===")
    
    try:
        # Inicjalizacja procesora
        print("1. Inicjalizacja procesora...")
        processor = NERProcessor()
        
        print("2. Ładowanie modelu...")
        processor.load_model()
        
        print("3. Test z prostym tekstem...")
        simple_text = "John works at Microsoft."
        entities = processor.recognize_entities(simple_text)
        print(f"Wynik: {entities}")
        
        print("4. Test z bardziej złożonym tekstem...")
        complex_text = "Donald Trump met with Vladimir Putin in Moscow."
        entities = processor.recognize_entities(complex_text)
        print(f"Wynik: {entities}")
        
    except Exception as e:
        print(f"BŁĄD: {e}")
        print(f"Typ błędu: {type(e)}")
        print("Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    debug_ner()
